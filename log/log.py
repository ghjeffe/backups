create table "hosts"
(
   "host_id" integer primary key not null autoincrement
    ,"hostname" text unique
    ,"last_known_ip" text
    ,"mac_addr" text check
        (
            length("mac_addr")  == 20
        )
)

create table "exec"
(
   "exec_id" integer primary key not null autoincrement
   ,"host_id" integer not null 
   ,"start_stamp" text 
   ,"end_stamp" text 
   ,"args" text 
)
create unique index "exec_host_idx"  on exec(exec_id, host_id) 
