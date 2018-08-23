def insert_msg_comment_tb(id,parent_id,content,to_who_uin_,create_time,owner):
    sql = "insert into msg_comment_tb  VALUES ('"+id+"','"+parent_id+"','"+content+"','"+to_who_uin_+"','"+create_time+"','"+owner+"');"
    return sql

def insert_qq_info_tb(id,qqnumber,nickname,img='-1'):
    sql = "call insert_qq_info('"+id+"','"+qqnumber+"','"+nickname+"','"+img+"');"
    return sql

def insert_frdship_tb(id,qqnumber,qqnumber2):
    sql = "call insert_frdship('"+id+"','"+qqnumber+"','"+qqnumber2+"');"
    return sql

def insert_msg_tb(id,qqnumber,content,source_name,createTime,like_cnt,type=0,img='-1'):
    sql = "call insert_msg('"+id+"','"+qqnumber+"','"+content+"','"+source_name+"','"+createTime+"',"+like_cnt+","+type+","
    sql = sql + '"'+img+'");'
    return sql

def insert_msg_like_tb(id,mood_id,qqnumber,sex,constellation):
    sql = "insert into msg_like_tb VALUES('"+id+"','"+ mood_id + "','" + qqnumber + "'," + sex + ",'"+constellation+"');"
    return sql
