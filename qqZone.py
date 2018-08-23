# -*- coding:utf-8 -*-
'''
@Date:2018-8-14
@Description:登陆QQ空间并获取cookie
@Source:https://www.cnblogs.com/txjwd/p/7269508.html
'''
from __future__ import unicode_literals
import configparser
from selenium import webdriver
import requests
import logging
import time
import os
import json
import re
from urllib import parse
from process import *
import uuid
import pymysql as mysql
from getSql import *


class User(object):
    def __init__(self, dir):
        config = configparser.ConfigParser(allow_no_value=False)
        config.read(dir)
        self.__username = config.get('my_info', 'number')
        self.__password = config.get('my_info', 'password')
        print('读取的账号信息为:number=' + self.__username)
        self.web = webdriver.Chrome()
        self.web.get('https://qzone.qq.com/')
        self.req = requests

        self.headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'zh-CN,zh;q=0.9',
            'Cookie': '',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'
        }
        print('初始化webdriver.chrom成功！')

        db = mysql.connect('localhost','root','root','qqZone')
        self.db = db
        self.log_file = open('./errorlog.txt','w+',encoding='utf-8')
        self.log_file.write('-----------------------'+str(time.asctime( time.localtime(time.time())))+'----------------')

    def __del__(self):
        self.db.close()
        self.log_file.close()
        self.web.close()



    def login(self):
        self.web.switch_to_frame('login_frame')
        # 跳转到账号密码登陆界面
        log = self.web.find_element_by_id("switcher_plogin")
        log.click()
        time.sleep(1)
        # 填充账号密码
        username = self.web.find_element_by_id('u')
        username.send_keys(self.__username)
        ps = self.web.find_element_by_id('p')
        ps.send_keys(self.__password)
        # 登陆按钮
        btn = self.web.find_element_by_id('login_button')
        time.sleep(1)
        btn.click()
        time.sleep(2)

        self.web.get('https://user.qzone.qq.com/{}'.format(self.__username))
        cookie = ''
        for elem in self.web.get_cookies():
            cookie += elem["name"] + "=" + elem["value"] + ";"
        self.cookies = cookie

        self.get_g_tk()
        self.headers['Cookie'] = self.cookies
        self.web.quit()
        print('登陆成功，headers = ' + str(self.headers))
        # html = self.web.page_source
        # g_qzonetoken = re.search('window\.g_qzonetoken = \(function\(\)\{ try\{return (.*?);\} catch\(e\)',html)  # 从网页源码中提取g_qzonetoken
        # g_qzonetoken = str(g_qzonetoken[0]).split('\"')[1]
        # self.qztoken = g_qzonetoken

    def get_g_tk(self):
        p_skey = self.cookies[self.cookies.find('p_skey=') + 7: self.cookies.find(';', self.cookies.find('p_skey='))]
        h = 5381
        for i in p_skey:
            h += (h << 5) + ord(i)
        # print('g_tk',h&2147483647)
        self.g_tk = h & 2147483647

    def get_friends_url(self):
        url = 'https://h5.qzone.qq.com/proxy/domain/base.qzone.qq.com/cgi-bin/right/get_entryuinlist.cgi?'
        params = {"uin": self.__username,
                  "fupdate": 1,
                  "action": 1,
                  "g_tk": self.g_tk}
        url = url + parse.urlencode(params)
        return url

    def get_friends_num(self):
        t = True
        offset = 0
        url = self.get_friends_url()
        while (t):
            url_ = url + '&offset=' + str(offset)
            page = self.req.get(url=url_, headers=self.headers,timeout = 60)
            if "\"uinlist\":[]" in page.text:
                t = False
            else:

                if not os.path.exists("./friends/"):
                    os.mkdir("friends/")
                with open('./friends/' + str(offset) + '.json', 'w', encoding='utf-8') as w:
                    w.write(page.text)
                offset += 50

    def get_friends_list(self):
        self.get_friends_num()
        k = 0
        file_list = [i for i in os.listdir('./friends/') if i.endswith('json')]
        friends_list = []
        for f in file_list:
            if len(f.split('.')[0]) < 5 and f.split('.')[0] != 'mood':
                with open('./friends/{}'.format(f), 'r', encoding='utf-8') as w:
                    data = w.read()[95:-5]
                    js = json.loads(data)
                    # print(js)
                    for i in js:
                        k += 1
                        friends_list.append(i)
                        '''
                        此处写入数据库好友信息，但是需要去重
                        '''
                        nickname = i['label']
                        id =getUuid()
                        qqnumber = i['data']
                        #第一步：去重，先做简单的去重   即去qq_info里面搜索qqnumber，搜索到了，则不插入，搜索不到则插入
                        sql = insert_qq_info_tb(id,qqnumber,nickname)
                        flag = execute_sql(sql,self.db)
                        if_success(flag,sql)

                        '''
                        此处还需写入好友关系表，同样需要去重，而且这次的去重是去掉重复的好友关系，即A-B与B-A也算重复
                        '''
                        sql = insert_frdship_tb(getUuid(),self.__username,i['data'])
                        if_success(execute_sql(sql,self.db),sql)

        print('获取好友信息:\n\t' + str(friends_list))
        if not os.path.exists('./friends'):
            os.mkdir('friends/')
        else:
            job = json.dumps(friends_list, ensure_ascii=False)
            with open('./friends/' + str(self.__username) + '.json', 'w', encoding='utf-8') as w:
                w.write(job)
                w.close()
            print('写入文件成功！')
        # 删除中间文件
        fl = os.listdir('./friends')
        for i in range(0, len(fl)):
            str1 = fl[i].split('.')[0]
            if len((str1)) < 4:
                os.remove('./friends/' + fl[i])
                print('删除文件' + './friends/' + fl[i])
        return friends_list

    # 整合说说的url
    def get_mood_url(self):
        url = 'https://h5.qzone.qq.com/proxy/domain/taotao.qq.com/cgi-bin/emotion_cgi_msglist_v6?'
        params = {
            "sort": 0,
            "ftype": 0,
            "num": 20,
            "cgi_host": "http://taotao.qq.com/cgi-bin/emotion_cgi_msglist_v6",
            "replynum": 100,
            "callback": "_preloadCallback",
            "code_version": 1,
            "inCharset": "utf-8",
            "outCharset": "utf-8",
            "notice": 0,
            "format": "jsonp",
            "need_private_comment": 1,
            "g_tk": self.g_tk
        }
        url = url + parse.urlencode(params)
        return url

    def get_mood_detail(self, friends_list):
        # friendPath = 'C:\\Users\\Administrator\\Desktop\\代码\\friends\\214704958.json'
        # moodPath = 'C:\\Users\\Administrator\\Desktop\\代码\\mood_detail'
        # l = readFriends(friendPath)
        # QQList = compareData(l, moodPath)
        url = self.get_mood_url()
        n = 0
        logFile = open('./friends/log.txt', 'a', encoding='utf-8')
        for u in friends_list:
            allList = []
            t = True
            QQ_number = u['data']
            # if  QQ_number in QQList:
            #     n +=1
            #     print(n)
            #     continue
            url_ = url + '&uin=' + str(QQ_number)
            pos = 0
            #访问好友说说
            while (t):
                #设置一次的返回数量
                url__ = url_ + '&pos=' + str(pos)
                # print(url__)
                mood_detail = self.req.get(url=url__, headers=self.headers,timeout = 60)
                print(QQ_number, u['label'], pos)
                if "\"msglist\":null" in mood_detail.text or "\"message\":\"对不起,主人设置了保密,您没有权限查看\"" in mood_detail.text:
                    t = False
                    if "\"message\":\"对不起,主人设置了保密,您没有权限查看\"" in mood_detail.text:
                        print(QQ_number + '对您设置了权限，不可访问')
                        logFile.write(QQ_number + '对您设置了权限，不可访问\n')
                else:
                    if not os.path.exists("./mood_detail/"):
                        os.mkdir("mood_detail/")
                    # if not os.path.exists("./mood_detail/"+u['label']):
                    #     os.mkdir("mood_detail/"+u['label'])
                    j = json.loads(mood_detail.text[17:-2])
                    try:
                        j1 = j['msglist']
                    except KeyError:
                        print('竟然没有msglist，惊了，赶紧存下来')
                        logFile.write('Error:'+str(j)+'\n')
                    list1 = msglist_process(j1,self.db,self.g_tk,self.req,self.headers,self.__username)
                    allList.extend(list1)
                pos += 20
            if len(allList)>0:
                with open('./mood_detail/' + QQ_number + '.json', 'w', encoding='utf-8') as w:
                    w.write(json.dumps(allList, ensure_ascii=False))
            time.sleep(2)
        logFile.close()
    '''
    获取单个说说下的所有评论
    '''
    def get_mood_comment_detail(self,uin,tid):
        url = self.get_mood_url()
        url = url + '&uin='+uin + '&tid=' + tid + '&pos=0'
        mood_comment_detail = self.req.get(url=url,headers=self.headers,timeout = 60)
        if "\"cmtnum\":0" in mood_comment_detail.text:
            print('该条说说无评论')
            return 0
        else:
            comment_json = json.loads(mood_comment_detail.text)
            comment_list = comment_json['commentlist']
            for item in comment_list:
                item_json = json.dumps(item,ensure_ascii=False)
                create_time = item_json['createTime2']#精确到秒的时间，需要转换类型
                comment_content = item_json['content']#评论内容
                comment_parent_id = tid#该条评论是tid的一级子评论
                comment_id = getUuid()
                comment_owner = item_json['owner']['uin']#发布者的uin
                '''
                此处应当对评论进行保存
                '''
                print('QQ号为:'+uin+'的说说tid为:'+tid+'的一条评论：uuid = '+comment_id+'\tcontent = '+comment_content)
                sql = insert_msg_comment_tb(comment_id, comment_parent_id, comment_content, uin, create_time, comment_owner)
                cursor = self.db.cursor()
                flag = execute_sql( sql, self.db)
                if not flag:
                    print('error in execute sql:' + sql)
                    self.log_file.write('error in execute sql:' + sql+'\n')
                mark = 0
                if item['list_3'] is not None:
                    #迭代评论的评论
                    for i in range(0,len(item['list_3'])):
                        i_json = json.dumps(item['list_3'][i],ensure_ascii=False)
                        id = getUuid()#唯一性标识
                        list_3_content = i_json['content'].split('}')[1]#内容
                        to_who = i_json['content'].split('}')[0].split(',')[0].split(':')[1]#to_who_uin
                        list_3_createTime2 = i_json['createTime2']#精确到秒的时间，需要转换类型
                        owner = i_json['owner']['uin']#发布者的uin
                        if i == 0:
                            parent_id = comment_id
                        else:
                            parent_id = mark

                        if  parent_id ==0:
                            print('错误的parent_id')
                            exit(0)
                        print('QQ号为:' + uin + '的说说tid为:' + tid + '的一条评论：uuid = ' + id + '\tcontent = ' + list_3_content)
                        '''
                        此处应当对评论进行保存
                        '''
                        sql = insert_msg_comment_tb(id,parent_id,list_3_content,to_who,list_3_createTime2,owner)
                        cursor = self.db.cursor()
                        flag = execute_sql(sql,self.db)
                        if not flag:
                            print('error in execute sql:'+sql)
                            self.log_file.write('error in execute sql:' + sql + '\n')
                        #每循环一次更新mark作为下一次自评论的parent
                        mark = id

if __name__ == '__main__':
    dirPath = 'C:\\Users\\Administrator\\Desktop\\代码\\userinfo.ini'
    user = User(dirPath)
    user.login()
    friendList = user.get_friends_list()
    user.get_mood_detail(friendList)

