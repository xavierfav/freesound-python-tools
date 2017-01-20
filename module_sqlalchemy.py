import sqlalchemy

def connect(user, password, db, host='localhost', port=5432):
    '''Returns a connection and a metadata object'''
    # We connect with the help of the PostgreSQL URL
    # postgresql://federer:grandestslam@localhost:5432/tennis
    url = 'postgresql://{}:{}@{}:{}/{}'
    url = url.format(user, password, host, port, db)

    # The return value of create_engine() is our connection object
    con = sqlalchemy.create_engine(url, client_encoding='utf8')

    # We then bind the connection to MetaData()
    meta = sqlalchemy.MetaData(bind=con, reflect=True)

    return con, meta


#EXAMPLE OF CREATING A TABLE:
#test = Table('test', meta,
#        Column('id', String),
#        Column('json', sqlalchemy.JSON)
#)

#
#t = test.insert().values(id='0', json={'f':'g'})
#conn.execute(t)
#r = meta.tables['test']
#for row in conn.execute(r.select()):
#    print row
