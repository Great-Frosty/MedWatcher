import schedule
import time

def job(arg):
    print(arg)

job_runner = schedule.Scheduler()
job_runner.every(2).seconds.do(job, arg='Alice').tag('alice')
job_jjojb = "job_runner.every(4).seconds.do(job, arg='Bob').tag('bob')"
exec(job_jjojb)
while True:
    job_runner.run_pending()
