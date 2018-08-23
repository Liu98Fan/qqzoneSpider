import json
import os
from qqZone import *
import pymysql
import time
from urllib import parse


sqlLogError = open('sqlerror.txt','a',encoding='utf8')
def get_moode_like_detai_url(g_tk,qq,tid):
    url = 'https://user.qzone.qq.com/proxy/domain/r.qzone.qq.com/cgi-bin/user/qz_opcnt2?'
    params = {
        'g_tk':g_tk,
        '_stp':str(time.time()).split('.')[0],
        'unikey':'http\\%3A\\%2F\\%2Fuser.qzone.qq.com\\%2F'+str(qq)+'\\%2Fmood\\%2F'+str(tid)+'.1',
        'face':'0',
        'fupdate':'1'
        # 'qzonetoken': qztoken
    }
    url = url + parse.urlencode(params)
    return url

def get_like_people_detail_url(g_tk,qq,tid,username):
    url = 'https://user.qzone.qq.com/proxy/domain/users.qzone.qq.com/cgi-bin/likes/get_like_list_app?'
    params = {
        'g_tk': g_tk,
        'unikey': 'http%3A%2F%2Fuser.qzone.qq.com%2F' + str(qq )+ '%2Fmood%2F' + str(tid )+ '.1',
        'uin':username,
        'query_count':'60'
        # 'qzonetoken':qztoken
        #缺失begin_uin和if_first_page
    }
    url = url + parse.urlencode(params)


    return url


def msglist_process(msg_list,db,g_tk,req,headers,username):
    msgJsonList = []
    for m in msg_list:
        msg_json_str = json.dumps(m,ensure_ascii=False)
        msg_json = json.loads(msg_json_str)
        content = msg_json['content']#说说内容
        creatTime = msg_json['createTime']#说说日期
        phone = msg_json['source_name']#手机型号
        tid = msg_json['tid']#说说的id
        qqnumber = msg_json['uin']#QQ号

        try:
            pic = msg_json['pic']  # 图片信息列表（没心情解析，先存再说T T）
        except KeyError:
            print('该用户说说没有图片')
            pic = ''
        try:
            if msg_json['rt_uin']!=None:
                type = 1#1表示转发
            else:
                type = 0#0表示原创
            if content=='':
                continue
        except KeyError:
            print('该用户说说是原创')
            type = 0
        '''
            这里开始要获取说说的点赞信息鸟
        '''
        url = get_moode_like_detai_url(g_tk,qqnumber,tid)
        like_detail = req.get(url = url,headers=headers,timeout = 60)
        data = json.loads(like_detail.text[10:-2])
        try:
            datalist = data['data'][0]
        except KeyError:
            print("Error:"+str(datalist))
            sqlLogError.write("Error:"+str(datalist)+'\n')
            continue
        if len(datalist)==1:
            like_cnt = datalist['current']['likedata']['cnt']#点赞人数
        else:
            print('error in get like_Data')

        sql = insert_msg_tb(tid,str(qqnumber),content,phone,creatTime,str(like_cnt),str(type),str(pic))
        flag = execute_sql(sql, db)
        if_success(flag,sql)
        msgJson = {"tid": tid, 'qqnumber': qqnumber, 'content': content, 'phone': phone,'phone':phone,'type':type,'pic':str(pic)}
        msgJsonList.append(msgJson)
        time.sleep(1)
        '''
        这里要开始获取哪些人赞了这个说说鸟
        '''
        if like_cnt==0:
            continue
        url = get_like_people_detail_url(g_tk,qqnumber,tid,username)
        #要合成url
        num = -1
        begin_uin = '0'
        while 1:
            if num==-1:
                url +='if_first_page=1&begin_uin=0'
            else:
                url +='if_first_page=0&begin_uin='+begin_uin
            people_like_detail = req.get(url=url, headers=headers,timeout = 60)
            data1 = json.loads(people_like_detail.text[11:-3])
            #这里是数据解析工作

            num = data1['data']['total_number']#本次加载总数
            if num==0:
                break;
            like_uin_info = data1['data']['like_uin_info']
            for i in range(0,num-1):
                temp_json = json.dumps(like_uin_info[i])
                fuin = temp_json['fuin']
                sex = temp_json['gender']
                portrait = temp_json['protrait']
                constellation = temp_json['constellation']
                id = getUuid()
                if i==num-1:
                    begin_uin = fuin
                #数据解析完毕，可以插入
                sql = insert_msg_like_tb(id,tid,fuin,sex,constellation)
                flag = execute_sql(sql,db)
                if_success(flag,sql)
    return msgJsonList

def readFriends(dir):
    if os.path.exists(dir):
        if os.path.isfile(dir):
            dataList = []
            with open(dir,'r',encoding='utf-8') as r:
                data = r.read()
            jsonData = json.loads(data)
            for j in jsonData:
                dataList.append(j['data'])
            return dataList
        else:
            print('path is not a file')
            exit(0)
    else:
        print('path does not exist')
        exit(0)
def getUuid():
    return ''.join( str(uuid.uuid1()).split('-'))
def compareData(friendList,dir):
    # QQNumberList = []
    # for key in friendList:
    #     QQNumberList.append(key)
    newlist = []
    if not os.path.exists(dir):
        print('path does not exist')
        exit(0)
    if not os.path.isdir(dir):
        print('path is not a dir')
        exit(0)
    fileList = os.listdir(dir)
    for i in range(0,len(fileList)):
        if '.json' in fileList[i]:
            number = int(fileList[i].split('.')[0])
            if number in friendList:
                continue
            else:
                newlist.append(number)
                print(number)
    return newlist

def execute_sql(sql,db):
    try:
        cursor = db.cursor()
        cursor.execute(sql)
        db.commit()
        return True
    except:
        print('sql执行错误')
        db.rollback()
        return False

def if_success(flag,sql='-1'):
    if not flag:
        print('error in executing sql')
        sqlLogError.write('error in execute sql:' + sql + '\n')
    else:
        print('success in executing sql')

if __name__ == '__main__':
    friendPath = 'C:\\Users\\Administrator\\Desktop\\代码\\friends\\214704958.json'
    moodPath = 'C:\\Users\\Administrator\\Desktop\\代码\\mood_detail'
    l = readFriends(friendPath)
    compareData(l,moodPath)


