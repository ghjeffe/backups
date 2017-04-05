import sqlite3

class Logger(object):

    def __init__(self, hostname, ip_addr='', mac_addr='', logfile='log.db'):
        self.hostname = hostname
        self.ip_addr = ip_addr
        self.mac_addr = mac_addr
        self._logfile = logfile
        self._conn = sqlite3.connect(self._logfile) #use ':memory' for testing
        self._host_id = self._get_host_id()

    def _db_init(self):
        tbls = ('''create table hosts
            (
               host_id integer primary key autoincrement not null
                ,hostname text unique
                ,ip_addr text
                ,mac_addr text check
                    (
                        length(mac_addr)  == 12
                    )
            )'''
            ,
            '''create table exec
            (
               exec_id integer primary key autoincrement not null
               ,host_id integer references hosts(host_id)
               ,start_stamp text
               ,end_stamp text
               ,args text
               ,foreign key(host_id) references hosts(host_id)
            )'''
            )
    
        idxs = ('''create unique index exec_host_idx on exec(exec_id, host_id)'''
            ,)
        
        for tbl in tbls:
            self._conn.execute(tbl)
        for idx in idxs:
            self._conn.execute(idx)
            
            
    def _get_host_id(self):
        sql_get_host = 'select host_id from hosts where hostname=?'
        host_id = self._conn.execute(sql_get_host, (self.hostname,)).fetchone()
        if not host_id:
            self._conn.execute(
                                 '''insert into hosts(hostname, ip_addr, mac_addr)
                                 values(?, ?, ?)'''
                                 ,(self.hostname, self.ip_addr, self.mac_addr)
                                 )
        
        host_id = self._cursor.execute(sql_get_host, (self.hostname,)).fetchone()
        return host_id[0]
    
    
    def log_exec(self, start_stamp, end_stamp, args):
        sql = '''insert into exec (host_id, start_stamp, end_stamp, args)
                values(?, ?, ?, ?)'''
        
        self._conn.execute(sql, (self._host_id ,start_stamp, end_stamp, args))