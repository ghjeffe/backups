import sqlite3
conn = sqlite3.connect('log.db')
cur = conn.cursor()

tbls = ('''create table hosts
(
   host_id integer primary key autoincrement not null
    ,hostname text unique
    ,last_known_ip text
    ,mac_addr text check
        (
            length(mac_addr)  == 12
        )
)'''
,
'''create table exec
(
   exec_id integer primary key autoincrement not null
   ,host_id integer not null
   ,start_stamp text
   ,end_stamp text
   ,args text
   ,foreign key(host_id) references hosts(host_id)
)'''
)

idxs = ('''create unique index exec_host_idx on exec(exec_id, host_id)'''
,)
