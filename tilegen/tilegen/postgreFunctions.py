import xml.etree.ElementTree as xml
import psycopg2
import sys
import time

def getDataInfos(source_params, extent, filter):
    x1 = str(extent[0])
    y1 = str(extent[1])
    x2 = str(extent[2])
    y2 = str(extent[3])
    polygon = 'POLYGON (('+x1+' '+ y1+','+ x1+' '+ y2+','+ x2+' '+ y2+','+ x2+' '+ y1+', '+x1+' '+ y1+' ))'
    con = None
    con = psycopg2.connect(database=source_params['dbname'], user=source_params['user'], port=source_params['port'], host=source_params['host'], password=source_params['password']) 
    cur = con.cursor()
    
    cur.execute("Select f_geometry_column from geometry_columns where f_table_name = '"+ source_params['table'] +"'")
    rows = cur.fetchall()
    column = str(rows[0]).replace('(','').replace(')','').replace("'",'').replace(',','')
    cur.execute("Select ST_SRID(" + column + ") from "+ source_params['table'])
    row = cur.fetchone()
    #print row
    srid = str(row).replace('(','').replace(')','').replace("'",'').replace(',','')
    #print srid
    
    command = "Select count(*) from "+ source_params['table']+" WHERE st_within(" + column + ", ST_GeometryFromtext('" + polygon + "'," + srid + "))"
    print command
    cur.execute(command)
    rows = cur.fetchall()
    #print rows[0]
    featCount = str(rows[0]).replace('(','').replace(')','').replace(",",'').replace("L",'')
    #print featCount
    con.commit()
    
    return featCount

def makePostgresTable(table_name, database_ud='meingis', user_ud='klammer'):    
        
    con = None

    con = psycopg2.connect(database = database_ud , user = user_ud) 
    cur = con.cursor()
    
    #Test if table 'geometry_columns' has already an entry for that table
    cur.execute("Select count(*) from geometry_columns where f_table_name = '"+ table_name +"'")
    ex = cur.fetchone()
    if ex[0] == 0:
        cur.execute("INSERT INTO geometry_columns VALUES('','public','%s','geom',2,900913,'GEOMETRY')"%table_name)

    cur.execute("DROP TABLE IF EXISTS %s"%table_name)
    cur.execute("CREATE TABLE "+ table_name +"(id integer NOT NULL, x integer NOT NULL, y integer NOT NULL, z integer NOT NULL, geom geometry, CONSTRAINT "+ table_name +"_pkey PRIMARY KEY (id, x, y, z)) WITH ( OIDS=FALSE); ALTER TABLE "+ table_name +" OWNER TO "+ user_ud +";")
    con.commit()

def writeToPostgres(file, table_name, database_ud='meingis', user_ud='klammer'):   

    con = None

    con = psycopg2.connect(database = database_ud , user = user_ud) 
    cur = con.cursor()

    tile = file.split('_')
    tile = (tile[1], tile[2], tile[3].split('.')[0])
    #print tile
       
    with open(file,'rt') as g:
        in_tree = xml.parse(g)
    counter = 0
    bbox = []
    round_val = 200
    for node in in_tree.iter('{http://www.opengis.net/gml}Box'):
        #get the bbox
        for part in node.iter():
            if part.tag == '{http://www.opengis.net/gml}coord':
                for subpart in part.iter():                        
                    if subpart.tag  == '{http://www.opengis.net/gml}X':
                        bbox.append(round(float(subpart.text),round_val))
                    elif subpart.tag  == '{http://www.opengis.net/gml}Y':
                        bbox.append(round(float(subpart.text),round_val))
    for node in in_tree.iter(tag = '{www.icaci.org/genmr/wps}Value'):
        start_time = time.time()
    
        #do this for linestrings
        if node.attrib['wpstype'] == 'AttributeTypeGeometryLineString' or node.attrib['wpstype'] == 'AttributeTypeGeometryPolygon':
            x = []
            y = []
            for part in node.iter(tag = '{http://www.opengis.net/gml}X'):
                x.append(part.text)
            for part in node.iter(tag = '{http://www.opengis.net/gml}Y'):
                y.append(part.text)
            
            if node.attrib['wpstype'] == 'AttributeTypeGeometryLineString':
                    strin = 'LINESTRING ('
                    strend = ')'
            elif node.attrib['wpstype'] == 'AttributeTypeGeometryPolygon':
                    strin = 'POLYGON ((' 
                    strend = '))'
            for i in xrange(len(x)):
                if i == 0:
                    strin = strin + str(round(float(x[i]),round_val)) + ' ' + str(round(float(y[i]),round_val))
                elif i == len(x) - 1:
                    strin = strin + ', ' + str(round(float(x[i]),round_val)) + ' ' + str(round(float(y[i]),round_val)) + strend
                else:
                    strin = strin + ', ' + str(round(float(x[i]),round_val)) + ' ' + str(round(float(y[i]),round_val))
            #print strin
            cur.execute("INSERT INTO "+ table_name +" VALUES("+str(counter)+","+str(tile[0])+","+str(tile[1])+","+str(tile[2])+",GeometryFromText ( '"+strin+"', 900913 ))")
            con.commit()
            
            counter = counter + 1
    
        #the rest hast to be implemented        
        #elif...
        
    #print counter
    

def makePostgresTableBbox(table_name = 'bbox'):    
        
    con = None

    con = psycopg2.connect(database='meingis', user='klammer') 
    cur = con.cursor()
    
    #Test if geometry_columns has already an entry for that table
    cur.execute("Select count(*) from geometry_columns where f_table_name = '"+ table_name +"'")
    ex = cur.fetchone()
    if ex[0] == 0:
        cur.execute("INSERT INTO geometry_columns VALUES('','public','bbox','geom',2,900913,'GEOMETRY')")

    cur.execute("DROP TABLE IF EXISTS bbox")
    #cur.execute("CREATE TABLE "+ table_name +"(id INT PRIMARY KEY, geom GEOMETRY) WITH (OIDS=TRUE)")
    cur.execute("CREATE TABLE "+ table_name +"(id integer, geom geometry) WITH ( OIDS=FALSE); ALTER TABLE bbox OWNER TO klammer;")
    #cur.execute("CREATE TABLE "+ table_name +"(id integer NOT NULL, x integer NOT NULL, y integer NOT NULL, z integer NOT NULL, geom geometry) WITH ( OIDS=FALSE); ALTER TABLE bbox OWNER TO klammer;")
    con.commit()

        
def writeBBoxToPostgres(val, extent, table_name = 'bbox'):  
    #print extent 
    x1 = str(extent[0])
    y1 = str(extent[1])
    x2 = str(extent[2])
    y2 = str(extent[3])
    polygon = 'LINESTRING ('+x1+' '+ y1+','+ x1+' '+ y2+','+ x2+' '+ y2+','+ x2+' '+ y1+', '+x1+' '+ y1+' )'
    #print polygon
    
    con = None

    con = psycopg2.connect(database='meingis', user='klammer') 
    cur = con.cursor()
    

    cur.execute("INSERT INTO bbox VALUES("+str(val)+", GeometryFromText ( '"+polygon+"', 900913 ))")
    con.commit()


###old Testing function
    
def postgresTest():
    #Source: http://zetcode.com/db/postgresqlpythontutorial/
    con = None

    try:
         
        con = psycopg2.connect(database='meingis', user='klammer') 
         
    
        cur = con.cursor()    
        cur.execute("SELECT ST_astext(geom) FROM generalized_line_cache")

        rows = cur.fetchall()

        for row in rows:
        
            print row  

    except psycopg2.DatabaseError, e:
            print 'Error %s' % e    
            sys.exit(1)
            
    finally:            
            if con:
                con.close()
            
