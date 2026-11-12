"""Creates the two practice subsets that fit GitHub's 25 MB upload limit.
usage: python make_subsets.py <pcards.db> <movies.db> <out_folder>"""
import sqlite3, os, sys
pc, mv, out = sys.argv[1:4]
def fresh(p):
    if os.path.exists(p): os.remove(p)
    return sqlite3.connect(p)
c = fresh(os.path.join(out, 'pcards_2014.db')); c.execute(f"attach '{pc}' as s")
c.execute(c.execute("select sql from s.sqlite_master where name='pcards'").fetchone()[0])
c.execute("insert into pcards select * from s.pcards where Year=2014"); c.commit(); c.execute('detach s'); c.execute('vacuum')
c = fresh(os.path.join(out, 'movies_subset.db')); c.execute(f"attach '{mv}' as s")
for (sql,) in c.execute("select sql from s.sqlite_master where type='table'").fetchall(): c.execute(sql)
c.execute("insert into movies select * from s.movies where id in (select movie_id from s.ratings where votes>=10000)")
for t in ['ratings', 'stars', 'directors']: c.execute(f"insert into {t} select * from s.{t} where movie_id in (select id from movies)")
c.execute("insert into people select * from s.people where id in (select person_id from stars union select person_id from directors)")
c.commit(); c.execute('detach s'); c.execute('vacuum')
