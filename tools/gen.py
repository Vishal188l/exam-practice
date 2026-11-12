"""Builds the question bank for the practice site.

Every correct answer and every common-mistake value is computed here from the
course data files, so nothing on the site is typed in by hand.
Output: site/data/bank.js
"""
import json, re, random, sqlite3, sys
from pathlib import Path
import numpy as np
import pandas as pd

MAT = Path(sys.argv[1])          # unzipped course materials
OUT = Path(sys.argv[2])          # site folder
DATA = Path(sys.argv[3])         # folder with prepared subsets (pcards_2014.db, movies_subset.db)

P = {
    'nyc': MAT / '1. Excel Part 1/PWC Excel Assignment/NYC_Film_Permits.txt',
    'nyc_sol': MAT / '1. Excel Part 1/PWC Excel Assignment/solutions.xlsx',
    'pay15': MAT / '1. Excel part 3/IntegrateCo Assignment/Analytics_mindset_case_studies_IntegrateCo_2015payroll.csv',
    'pay16': MAT / '1. Excel part 3/IntegrateCo Assignment/Analytics_mindset_case_studies_IntegrateCo_2016payroll.csv',
    'jobs': MAT / '1. Excel part 3/IntegrateCo Assignment/Analytics_mindset_case_studies_IntegrateCo_jobcodes.csv',
    'loc': MAT / '1. Excel part 3/IntegrateCo Assignment/Analytics_mindset_case_studies_IntegrateCo_locations.csv',
    'etl2': MAT / '1. Excel part 2/ETL Assignment/data/case 2/Analytics_mindset_case_studies_ETL_Case2_Excel.xlsx',
    'etl3': MAT / '1. Excel part 2/ETL Assignment/data/case 3/Analytics_mindset_case_studies_ETL_Case3_Excel.xlsx',
    'etl4': MAT / '1. Excel part 2/ETL Assignment/data/case 4/Analytics_mindset_case_studies_ETL_Case4_Excel.xlsx',
    'rest': MAT / '1. Excel part 4/Regression Assignment/Restaurant/data.xlsm',
    'chinook': MAT / '2. SQL part 1/Assignments/pwc assignment/Chinook_Sqlite.sqlite',
    'songs': MAT / '2. SQL part 1/Assignments/cs50 assignment/songs/songs.db',
    'movies': DATA / 'movies_subset.db',
    'pcards': DATA / 'pcards_2014.db',
}

QUESTIONS = []

def r(x, d=2):
    return float(round(float(x), d))

def add(dataset, tool, skills, text, check, solution, mistakes=(), secs=90, source=None):
    """check: dict(type=number|text|choice, answer, dec, pct, options, prompt)"""
    ans = check['answer']
    ms = []
    for val, why in mistakes:
        if val is None:
            continue
        if check['type'] == 'number':
            if pd.isna(val):
                continue
            val = float(val)
            tol = 0.5 * 10 ** (-check.get('dec', 0)) + 1e-9
            if abs(val - float(ans)) <= tol:   # mistake gives same number -> not diagnostic here
                continue
            if any(abs(val - m['value']) <= tol for m in ms):
                continue
            ms.append({'value': r(val, check.get('dec', 0) + 2), 'why': why})
        else:
            if str(val).strip().lower() == str(ans).strip().lower():
                continue
            ms.append({'value': str(val), 'why': why})
    if check['type'] == 'number':
        check['answer'] = r(ans, check.get('dec', 0))
    QUESTIONS.append(dict(dataset=dataset, tool=tool, skills=list(skills), text=text,
                          check=check, solution=solution, mistakes=ms, secs=secs, source=source))

def num(answer, dec=0, prompt=None, pct=False):
    return dict(type='number', answer=answer, dec=dec, pct=pct, prompt=prompt)

def txt(answer, prompt=None, accept=()):
    return dict(type='text', answer=str(answer), accept=[str(a) for a in accept], prompt=prompt)

def choice(options, correct, prompt=None):
    return dict(type='choice', options=options, answer=correct, prompt=prompt)

def dec_word(d):
    return {0: 'a whole number', 1: 'one decimal', 2: 'two decimals', 3: 'three decimals'}[d]

# ---------------------------------------------------------------- NYC film permits (Excel)
def nyc():
    df = pd.read_csv(P['nyc'], dtype=str)
    fmt = '%m/%d/%Y %H:%M'
    for c in ['StartDateTime', 'EndDateTime', 'EnteredOn']:
        df[c + '_us'] = pd.to_datetime(df[c], format=fmt)
        # Danish regional settings: Excel reads 7/11/2016 as 7 November; 7/18/2016 stays text
        df[c + '_dk'] = pd.to_datetime(df[c], format='%d/%m/%Y %H:%M', errors='coerce')
    s = df[df.EventType == 'Shooting Permit']
    dur = (s.EndDateTime_us - s.StartDateTime_us).dt.total_seconds() / 3600
    dur_dk = (s.EndDateTime_dk - s.StartDateTime_dk).dt.total_seconds() / 3600
    dur_all = (df.EndDateTime_us - df.StartDateTime_us).dt.total_seconds() / 3600
    DK = "This is what you get when Excel reads the US dates (month/day/year) with Danish regional settings (day/month/year): dates like 7/18/2016 stay as text and 7/11/2016 becomes 7 November. Re-import with Data > From Text/CSV and set the locale to English (United States)."
    ALL = "You included every EventType. The question is only about shooting permits — filter EventType = \"Shooting Permit\" first."
    SOL_IMPORT = "Import with Data > From Text/CSV, File origin/locale = English (United States), so StartDateTime, EndDateTime and EnteredOn become real dates."

    # original assignment questions (answers from the course solutions file, re-computed here)
    sol = pd.read_excel(P['nyc_sol'], header=1)
    a = {int(i): v for i, v in zip(sol['Index'], sol['Answer'])}
    assert len(df) == a[1] and df.shape[1] - 6 == a[2]
    add('nyc', 'Excel', ['import', 'count'], 'How many records does the permit table have (excluding the header)?',
        num(len(df)), SOL_IMPORT + " Then =COUNTA(A:A)-1.",
        [(len(df) + 1, "You counted the header row as a record.")], 45, 'Assignment 1')
    assert s.Category.value_counts().index[0] == a[10]
    st = (s.Category == 'Student').sum()
    assert st == a[11]
    add('nyc', 'Excel', ['conditional count'], 'How many shooting permits were granted for student films?',
        num(st), 'Pivot table: filter EventType = Shooting Permit, rows = Category, values = count of EventID. Or =COUNTIFS(B:B,"Shooting Permit",K:K,"Student").',
        [((df.Category == 'Student').sum(), ALL)], 60, 'Assignment 1')
    avgd = dur.mean()
    assert round(avgd * 2) / 2 == a[16]
    add('nyc', 'Excel', ['date arithmetic', 'aggregate'], 'What is the average duration of a shooting permit in hours? Round to two decimals.',
        num(avgd, 2), SOL_IMPORT + ' Add a column =(EndDateTime-StartDateTime)*24 and take AVERAGEIFS(duration, EventType, "Shooting Permit").',
        [(avgd / 24, "You left the duration in days. Excel stores dates as days, so multiply the difference by 24 to get hours."),
         (dur_all.mean(), ALL), (dur_dk.mean(), DK)], 90, 'Assignment 1')
    lead = (s.StartDateTime_us - s.EnteredOn_us).dt.total_seconds() / 86400
    assert round(lead.mean()) == a[18]
    add('nyc', 'Excel', ['date arithmetic', 'aggregate'], 'What is the average lead time in days between EnteredOn and StartDateTime for shooting permits? Round to two decimals.',
        num(lead.mean(), 2), SOL_IMPORT + ' Add =StartDateTime-EnteredOn and average it for shooting permits.',
        [(-lead.mean(), "Your sign is flipped: subtract EnteredOn from StartDateTime."),
         (((s.StartDateTime_dk - s.EnteredOn_dk).dt.total_seconds() / 86400).mean(), DK)], 90, 'Assignment 1')
    dow = s.StartDateTime_us.dt.day_name().value_counts().index[0]
    assert dow == a[19]
    add('nyc', 'Excel', ['date functions', 'summary'], 'On which day of the week do most shooting permits start? Give the full day name.',
        txt(dow), 'Add =TEXT(StartDateTime,"dddd") and count by it in a pivot table.',
        [(s.StartDateTime_dk.dt.day_name().value_counts().index[0], DK)], 60, 'Assignment 1')

    boroughs = ['Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island']
    for B in boroughs:
        sb, db = s[s.Borough == B], df[df.Borough == B]
        durb = (sb.EndDateTime_us - sb.StartDateTime_us).dt.total_seconds() / 3600
        add('nyc', 'Excel', ['conditional count'], f'How many shooting permits were issued in {B}?',
            num(len(sb)), f'=COUNTIFS(EventType,"Shooting Permit",Borough,"{B}") or a pivot table with both filters.',
            [(len(db), ALL), (len(s), f"You counted shooting permits in every borough — add the Borough = {B} condition.")], 60)
        add('nyc', 'Excel', ['date arithmetic', 'filter', 'aggregate'], f'What is the average duration in hours of shooting permits in {B}? Round to two decimals.',
            num(durb.mean(), 2), SOL_IMPORT + f' Duration =(EndDateTime-StartDateTime)*24, then AVERAGEIFS(duration,EventType,"Shooting Permit",Borough,"{B}").',
            [(durb.mean() / 24, "You left the duration in days — multiply by 24."),
             (((db.EndDateTime_us - db.StartDateTime_us).dt.total_seconds() / 3600).mean(), ALL),
             (((sb.EndDateTime_dk - sb.StartDateTime_dk).dt.total_seconds() / 3600).mean(), DK)], 90)
        add('nyc', 'Excel', ['date arithmetic', 'conditional count'], f'How many shooting permits in {B} lasted more than 24 hours?',
            num((durb > 24).sum()), f'Duration column in hours, then =COUNTIFS(EventType,"Shooting Permit",Borough,"{B}",Duration,">24").',
            [((durb >= 24).sum(), "You used ≥ 24. \"More than 24 hours\" means > 24, so permits of exactly 24 hours are excluded."),
             ((durb > 1).sum(), "You compared days with 24 — the duration must be in hours (difference × 24) before comparing with 24."),
             ((((sb.EndDateTime_dk - sb.StartDateTime_dk).dt.total_seconds() / 3600) > 24).sum(), DK)], 90)
        add('nyc', 'Excel', ['text filter', 'conditional count'], f'How many shooting permits in {B} have BROADWAY anywhere in ParkingHeld?',
            num(sb.ParkingHeld.str.contains('BROADWAY', case=False, na=False).sum()),
            f'=COUNTIFS(EventType,"Shooting Permit",Borough,"{B}",ParkingHeld,"*BROADWAY*") — the * wildcards match text anywhere in the cell.',
            [(db.ParkingHeld.str.contains('BROADWAY', case=False, na=False).sum(), ALL),
             (sb.ParkingHeld.str.upper().str.startswith('BROADWAY').sum(), "You only matched cells that START with BROADWAY. Use \"*BROADWAY*\" to match it anywhere."),
             ((sb.ParkingHeld.str.upper() == 'BROADWAY').sum(), "You matched cells that equal BROADWAY exactly. Use wildcards: \"*BROADWAY*\".")], 75)
        cat = sb.Category.value_counts()
        add('nyc', 'Excel', ['summary', 'ranking'], f'What is the most common Category of shooting permit in {B}?',
            txt(cat.index[0]), 'Pivot table: filter EventType = Shooting Permit and Borough; rows = Category; values = count; sort descending.',
            [(db.Category.value_counts().index[0], ALL)], 60)
        tv = (sb.Category == 'Television').mean() * 100
        add('nyc', 'Excel', ['conditional count', 'percentage'], f'What percentage of shooting permits in {B} are in the Television category? Give a percentage with one decimal (e.g. 45.3).',
            num(tv, 1, pct=True), 'Count Television shooting permits in the borough and divide by all shooting permits in the borough.',
            [((db.Category == 'Television').mean() * 100, ALL),
             ((sb.Category == 'Television').sum() / len(s) * 100, "You divided by shooting permits in ALL boroughs. The denominator should be the borough's shooting permits.")], 90)
    for Y in range(2012, 2018):
        sy = s[s.StartDateTime_us.dt.year == Y]
        add('nyc', 'Excel', ['date filter', 'count'], f'How many shooting permits started in {Y}?',
            num(len(sy)), SOL_IMPORT + f' Add =YEAR(StartDateTime) and =COUNTIFS(EventType,"Shooting Permit",StartYear,{Y}).',
            [((s.EnteredOn_us.dt.year == Y).sum(), "You used the year of EnteredOn (when the permit was entered). The question asks about StartDateTime."),
             ((df.StartDateTime_us.dt.year == Y).sum(), ALL),
             ((s.StartDateTime_dk.dt.year == Y).sum(), DK)], 75)
        ly = (sy.StartDateTime_us - sy.EnteredOn_us).dt.total_seconds() / 86400
        add('nyc', 'Excel', ['date arithmetic', 'aggregate'], f'What is the average lead time in days between EnteredOn and StartDateTime for shooting permits starting in {Y}? Round to two decimals.',
            num(ly.mean(), 2), f'Lead time =StartDateTime-EnteredOn; then AVERAGEIFS(lead,EventType,"Shooting Permit",StartYear,{Y}).',
            [(-ly.mean(), "Your sign is flipped: StartDateTime − EnteredOn."),
             (((s[s.EnteredOn_us.dt.year == Y].StartDateTime_us - s[s.EnteredOn_us.dt.year == Y].EnteredOn_us).dt.total_seconds() / 86400).mean(),
              "You selected permits by the year of EnteredOn instead of StartDateTime."),
             (((s[s.StartDateTime_dk.dt.year == Y].StartDateTime_dk - s[s.StartDateTime_dk.dt.year == Y].EnteredOn_dk).dt.total_seconds() / 86400).mean(), DK)], 90)
        vb = sy.Borough.value_counts()
        add('nyc', 'Excel', ['summary', 'ranking'], f'Which borough had the most shooting permits starting in {Y}?',
            txt(vb.index[0]), 'Pivot table: filter EventType and start year; rows = Borough; sort count descending.',
            [(df[df.StartDateTime_us.dt.year == Y].Borough.value_counts().index[0], ALL)], 60)

# ---------------------------------------------------------------- IntegrateCo payroll (Excel)
def payroll():
    p15 = pd.read_csv(P['pay15'], sep='|', dtype={'Job': str})
    p16 = pd.read_csv(P['pay16'], sep='|', dtype={'Project': str, 'Employee_Number': str})
    jobs = pd.read_csv(P['jobs'], sep='|', dtype=str)
    loc = pd.read_csv(P['loc'], sep='|')
    jc = lambda s: s.str.extract(r'^\d{2}[A-Za-z]?(\d{3})')[0]
    p15['jc'] = jc(p15.Job); p16['jc'] = jc(p16.Project)
    p15['mid'] = p15.Job.str[2:5]; p16['mid'] = p16.Project.str[2:5]
    p15['gross'] = p15.Reg_Pay + p15.OT_Pay
    p15['hrs'] = p15.Reg_Hrs + p15.OT_Hrs
    p16['hrs'] = p16.Hours + p16.OT_Hours
    MID = "You extracted the job code with MID(Job,3,3). Codes such as 14H002 or 15S001SG have a department letter after the year, so MID returns \"H00\" and those rows drop out. Strip the letter first, e.g. =IF(ISNUMBER(--MID(A2,3,1)),MID(A2,3,3),MID(A2,4,3))."
    SOLJC = 'Extract the job code: =IF(ISNUMBER(--MID(Job,3,1)),MID(Job,3,3),MID(Job,4,3)) (stored as text, e.g. "002").'
    names = dict(zip(jobs.Job_Code, jobs.Job_Description))
    for J in sorted(jobs.Job_Code):
        a15 = p15[p15.jc == J]; a16 = p16[p16.jc == J]
        if len(a15) == 0 and len(a16) == 0:
            continue
        nm = f'{J} ({names[J]})'
        if len(a15):
            add('payroll15', 'Excel', ['text extraction', 'conditional sum'], f'What was the total 2015 gross pay (regular + overtime pay) for job code {nm}? Round to two decimals.',
                num(a15.gross.sum(), 2), SOLJC + ' Add Gross = Reg_Pay + OT_Pay, then SUMIFS(Gross, JobCode, "' + J + '").',
                [(a15.Reg_Pay.sum(), "You summed Reg_Pay only. Gross pay in 2015 = Reg_Pay + OT_Pay (that is how 2016 Gross_Wages is defined)."),
                 (p15[p15.mid == J].gross.sum(), MID),
                 (a15.gross.sum() + a15.Futa.sum() + a15.Suta.sum() + a15.Fica_Medc.sum() + a15.Work_Comp.sum(), "You added the taxes (Futa, Suta, Fica_Medc, Work_Comp). Gross pay is wages only.")], 120)
            add('payroll15', 'Excel', ['text extraction', 'conditional sum'], f'How many hours (regular + overtime) were recorded on job code {nm} in 2015? Round to two decimals.',
                num(a15.hrs.sum(), 2), SOLJC + ' Then SUMIFS of Reg_Hrs + SUMIFS of OT_Hrs for the job code.',
                [(a15.Reg_Hrs.sum(), "You only counted Reg_Hrs — add OT_Hrs."), (p15[p15.mid == J].hrs.sum(), MID)], 100)
        if len(a16):
            add('payroll16', 'Excel', ['text extraction', 'conditional sum'], f'What were the total 2016 gross wages for job code {nm}? Round to two decimals.',
                num(a16.Gross_Wages.sum(), 2), SOLJC.replace('Job', 'Project') + ' Then SUMIFS(Gross_Wages, JobCode, "' + J + '").',
                [(p16[p16.mid == J].Gross_Wages.sum(), MID.replace('Job', 'Project'))], 100)
            g = a16.Gross_Wages.sum() / a16.hrs.sum() if a16.hrs.sum() else np.nan
            if not pd.isna(g):
                add('payroll16', 'Excel', ['text extraction', 'ratio'], f'What was the 2016 gross pay per hour (gross wages ÷ (Hours + OT_Hours)) for job code {nm}? Round to two decimals.',
                    num(g, 2), 'Sum Gross_Wages and sum Hours + OT_Hours for the job code, then divide the totals (do not average row-level rates).',
                    [(a16.Gross_Wages.sum() / a16.Hours.sum() if a16.Hours.sum() else None, "You divided by regular Hours only — include OT_Hours."),
                     ((a16.Gross_Wages / a16.hrs.replace(0, np.nan)).mean(), "You averaged the per-row hourly rates. Divide total wages by total hours instead (a weighted average).")], 120)
        if len(a15) and len(a16):
            d = a16.Gross_Wages.sum() - a15.gross.sum()
            add('payroll15', 'Excel', ['combine years', 'difference'], f'By how much did gross pay for job code {nm} change from 2015 to 2016 (2016 minus 2015)? Round to two decimals.',
                num(d, 2), 'Build a job-code table with 2015 gross (Reg_Pay + OT_Pay) and 2016 Gross_Wages, then subtract 2015 from 2016. Positive = 2016 was higher.',
                [(-d, "You subtracted the wrong way round: the case defines the difference as 2016 − 2015."),
                 (a16.Gross_Wages.sum() - a15.Reg_Pay.sum(), "Your 2015 figure excludes OT_Pay."),
                 (p16[p16.mid == J].Gross_Wages.sum() - p15[p15.mid == J].gross.sum(), MID)], 150)
    # Part 4 questions
    ph = p16[p16.Employee_Number.isna() | (p16.Employee_Number.str.strip() == '')]
    add('payroll16', 'Excel', ['data quality', 'count'], 'How many 2016 payroll rows were entered without an employee number ("phantom" entries)?',
        num(len(ph)), 'Filter Employee_Number for blanks, or =COUNTBLANK(Employee_Number column).',
        [(p16.Employee_ID.isna().sum(), "You looked for a blank Employee_ID. The question is about Employee_Number.")], 60, 'IntegrateCo P4 Q3')
    add('payroll16', 'Excel', ['data quality', 'conditional sum'], 'What is the total gross wage amount of the 2016 rows without an employee number? Round to two decimals.',
        num(ph.Gross_Wages.sum(), 2), '=SUMIFS(Gross_Wages, Employee_Number, "") — sums wages where the employee number is blank.', [], 75, 'IntegrateCo P4 Q3')
    tot = (p16.Gross_Wages + p16.SocSec_Medicare + p16.FUTA + p16.SUTA + p16.Work_Comp).sum()
    add('payroll16', 'Excel', ['aggregate'], 'What was the total employee cost in 2016 (gross wages + Social Security/Medicare + FUTA + SUTA + workers\' compensation)? Round to two decimals.',
        num(tot, 2), 'Sum the five columns: =SUM(Gross_Wages, SocSec_Medicare, FUTA, SUTA, Work_Comp) over all rows.',
        [(p16.Gross_Wages.sum(), "You only summed Gross_Wages. Total employee cost also includes the employer taxes and workers' comp."),
         (tot - p16.Work_Comp.sum(), "You left out Work_Comp.")], 75, 'IntegrateCo P4 Q5')
    p15['name'] = p15.First_Name + ' ' + p15.Last_Name
    ot = p15.groupby(['Emp_No', 'name']).OT_Pay.sum().sort_values(ascending=False)
    add('payroll15', 'Excel', ['summary', 'ranking'], 'Which employee earned the most overtime pay in the first six months of 2015? Give the full name (First Last).',
        txt(ot.index[0][1]), 'Pivot table on 2015 data: rows = Emp_No and name, values = sum of OT_Pay; sort descending.',
        [(p15.groupby('name').OT_Hrs.sum().idxmax(), "That employee has the most overtime HOURS. The question is about overtime PAY.")], 75, 'IntegrateCo P4 Q1')
    add('payroll15', 'Excel', ['summary', 'ranking'], 'How much overtime pay did the top overtime earner receive in the first six months of 2015? Round to two decimals.',
        num(ot.iloc[0], 2), 'Same pivot table as above — read the top value.', [], 60, 'IntegrateCo P4 Q1')
    pp = p15.groupby(['name', 'Pay_Date']).agg(reg=('Reg_Hrs', 'sum'), ot=('OT_Hrs', 'sum')).reset_index()
    bad = pp[(pp.reg < 40) & (pp.ot > 0)]
    rowbad = p15[(p15.Reg_Hrs < 40) & (p15.OT_Hrs > 0)]
    add('payroll15', 'Excel', ['summary', 'control test'], 'In 2015, on how many employee-pay-date combinations did an employee record overtime while having fewer than 40 regular hours on that pay date?',
        num(len(bad)), 'Pivot table: rows = employee name and Pay_Date; values = sum of Reg_Hrs and sum of OT_Hrs. Count rows with Reg < 40 and OT > 0 (sum per pay date first!).',
        [(len(rowbad), "You tested each payroll row on its own. An employee's hours are split across job codes, so first total Reg_Hrs and OT_Hrs per employee per pay date.")], 150, 'IntegrateCo P4 Q4')
    p15['month'] = pd.to_datetime(p15.Pay_Date, format='%m/%d/%Y').dt.month
    mg = p15.groupby('month').gross.sum()
    mname = lambda m: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'][m - 1]
    p15['month_dk'] = pd.to_datetime(p15.Pay_Date, format='%d/%m/%Y', errors='coerce').dt.month
    add('payroll15', 'Excel', ['date functions', 'summary'], 'In which month of 2015 were gross wages (Reg_Pay + OT_Pay) highest? Give the month name.',
        txt(mname(mg.idxmax())), 'Add =MONTH(Pay_Date) (dates imported as US m/d/yyyy), pivot by month, sum of gross.',
        [(mname(int(p15.groupby('month_dk').gross.sum().idxmax())), "Your months come from US dates read with Danish settings (day/month). 1/2/2015 is 2 January, not 1 February — re-import with the English (United States) locale.")], 90, 'IntegrateCo P4 Q8')
    for m in range(1, 7):
        diff = mg[m] - mg.mean()
        add('payroll15', 'Excel', ['date functions', 'summary'], f'How much did 2015 gross wages in {mname(m)} differ from the average monthly gross wages of January–June 2015 (month minus average)? Round to two decimals.',
            num(diff, 2), 'Pivot gross wages by MONTH(Pay_Date); average the six monthly totals; subtract the average from the month.',
            [(-diff, "Sign flipped: month minus average."),
             (p15[p15.month == m].gross.mean() - p15.gross.mean(), "You compared average ROW amounts. Compare monthly TOTALS with the average monthly total.")], 120, 'IntegrateCo P4 Q8')
    m15 = p15.merge(loc, left_on='name', right_on='Employee_Name', how='left')
    p16n = p16[~(p16.Employee_Number.isna())]
    m16 = p16n.merge(loc, on='Employee_Name', how='left')
    for L in [1, 2]:
        a, b = m15[m15.Location == L], m16[m16.Location == L]
        add('payroll15', 'Excel', ['lookup', 'conditional sum'], f'Using the locations file, how many hours (regular + overtime) did employees at location {L} work in 2015? Round to two decimals.',
            num(a.hrs.sum(), 2), 'Add a Location column with XLOOKUP(First_Name&" "&Last_Name, locations[Employee_Name], locations[Location]); then SUMIFS of Reg_Hrs + OT_Hrs.',
            [(a.Reg_Hrs.sum(), "You only counted regular hours.")], 150, 'IntegrateCo P4 Q6')
        add('payroll16', 'Excel', ['lookup', 'ratio'], f'Using the locations file, what was the 2016 average gross pay per hour at location {L} (gross wages ÷ (Hours + OT_Hours))? Exclude rows without an employee number. Round to two decimals.',
            num(b.Gross_Wages.sum() / b.hrs.sum(), 2), 'Look up Location by Employee_Name, then divide total Gross_Wages by total hours for the location.',
            [(b.Gross_Wages.sum() / b.Hours.sum(), "You divided by regular Hours only.")], 150, 'IntegrateCo P4 Q6')

# ---------------------------------------------------------------- ETL cases 2-4 (Excel)
def etl():
    c2 = pd.read_excel(P['etl2'], sheet_name='Case 2')
    c2['loc'] = c2.EmployeeCode.str[:3]
    c2['plant'] = c2.EmployeeCode.str.extract(r'-(\d+)')[0]
    c2['pay'] = c2.EmployeeCode.str[-1]
    names = {'ARG': 'Argentina', 'AUS': 'Australia', 'CAN': 'Canada', 'ENG': 'England', 'GER': 'Germany', 'JAP': 'Japan', 'MEX': 'Mexico', 'USA': 'the USA'}
    for L, nm in names.items():
        x = c2[c2['loc'] == L]
        add('plants2', 'Excel', ['text extraction', 'count'], f'Case 2 data: how many employees work in {nm} (location code {L})?',
            num(len(x)), '=COUNTIF(Location,"' + L + '") after Location =LEFT(EmployeeCode,3).',
            [(c2.EmployeeCode.str.contains(L).sum(), f"You searched for {L} anywhere in the code; it only counts as the first three characters.")], 45)
        add('plants2', 'Excel', ['text extraction', 'conditional count'], f'Case 2 data: how many employees in {nm} are paid weekly?',
            num(((c2['loc'] == L) & (c2.pay == 'W')).sum()), 'PayPeriod =RIGHT(EmployeeCode,1); =COUNTIFS(Location,"' + L + '",PayPeriod,"W").',
            [((c2.pay == 'W').sum(), f"You counted weekly employees in all countries — add the Location = {L} condition.")], 60)
        add('plants2', 'Excel', ['text extraction', 'unique identifier'], f'Case 2 data: how many different plants (LocationPlantID values such as {L}-12) are there in {nm}?',
            num(x.plant.nunique()), 'PlantID =MID(EmployeeCode,FIND("-",EmployeeCode)+1,2); LocationPlantID =Location&"-"&PlantID; count unique values for the country (e.g. pivot table rows, or =COUNTA(UNIQUE(FILTER(...)))).',
            [(c2.plant.nunique(), "You counted unique PlantIDs across all countries. Plant numbers restart in every country, which is why LocationPlantID is needed.")], 90)
    add('plants2', 'Excel', ['unique identifier'], 'Case 2 data: how many unique LocationPlantID values are there in total?',
        num((c2['loc'] + '-' + c2.plant).nunique()), 'Combine =Location&"-"&PlantID and count the distinct values.',
        [(c2.plant.nunique(), "You counted distinct PlantIDs only. Plant 12 in Germany and plant 12 in Japan are different plants — combine with Location.")], 90)
    c3 = pd.read_excel(P['etl3'], sheet_name='Case 3 data')
    c3['loc'] = c3.EmployeeCode.str.extract(r'^([A-Za-z]+)')[0]
    c3['pay'] = c3.EmployeeCode.str.extract(r'([A-Za-z]+)$')[0]
    mo = c3.pay.isin(['M', 'Mo']).sum()
    add('plants3', 'Excel', ['messy text', 'conditional count'], 'Case 3 data: how many employees are paid monthly?',
        num(mo), 'Extract PayPeriod as the trailing letters, then count both "M" and "Mo": =COUNTIF(P,"M")+COUNTIF(P,"Mo"), or =COUNTIF(P,"M*").',
        [((c3.pay == 'M').sum(), 'You only counted "M". In Case 3, "Mo" also means monthly.'),
         ((c3.pay == 'Mo').sum(), 'You only counted "Mo". "M" also means monthly.')], 90)
    wk = c3.pay.isin(['W', 'We']).sum()
    add('plants3', 'Excel', ['messy text', 'conditional count'], 'Case 3 data: how many employees are paid weekly?',
        num(wk), 'Count both "W" and "We" (e.g. =COUNTIF(P,"W*")).',
        [((c3.pay == 'W').sum(), 'You only counted "W" — "We" also means weekly.')], 90)
    c3names = {'ARG': 'Argentina', 'AUS': 'Australia', 'Canada': 'Canada', 'ENG': 'England', 'GER': 'Germany', 'Japan': 'Japan', 'MEX': 'Mexico', 'US': 'the USA'}
    for L, nm in c3names.items():
        x = c3[c3['loc'] == L]
        if not len(x):
            continue
        add('plants3', 'Excel', ['messy text', 'count'], f'Case 3 data: how many employees work in {nm}?',
            num(len(x)), f'Location is all letters before the first digit (here "{L}"). Extract it with a formula that finds the first digit, e.g. =LEFT(A2,MIN(FIND({{0,1,2,3,4,5,6,7,8,9}},A2&"0123456789"))-1).',
            [(c3.EmployeeCode.str[:3].eq(L[:3]).sum() if len(L) != 3 else None, "You took the first three characters, but in Case 3 some codes are longer (Canada, Japan) or shorter (US).")], 90)
        add('plants3', 'Excel', ['messy text', 'unique identifier'], f'Case 3 data: how many different plants are there in {nm}?',
            num(x.EmployeeCode.str.extract(r'-(\d+)')[0].nunique()), 'PlantID = digits after the hyphen (before the pay-period letters). Count unique values for the country.', [], 120)
    je = pd.read_excel(P['etl4'], sheet_name='JELineItems')
    bu = pd.read_excel(P['etl4'], sheet_name='BusinessUnits')
    coa = pd.read_excel(P['etl4'], sheet_name='ChartOfAccounts').iloc[:, :4]
    prep = pd.read_excel(P['etl4'], sheet_name='PreparerInfo')
    src = pd.read_excel(P['etl4'], sheet_name='Source')
    prep['nm'] = prep.PreparerName.str.split('|').str[0].str.strip()
    je['Debit'] = pd.to_numeric(je.Debit, errors='coerce').fillna(0)
    m = je.merge(bu, on='BusinessUnitID').merge(coa, on='GLAccountNumber', how='left').merge(prep, on=['PreparerID', 'BusinessUnitID'], how='left').merge(src, on='SourceID', how='left')
    first = prep.drop_duplicates('PreparerID')[['PreparerID', 'nm']].rename(columns={'nm': 'nm_v'})
    m = m.merge(first, on='PreparerID', how='left')
    for b in bu.BusinessUnit:
        add('journal', 'Excel', ['lookup', 'conditional sum'], f'Journal entries (Case 4): what is the total debit amount for business unit {b.title()}? Round to two decimals.',
            num(m[m.BusinessUnit == b].Debit.sum(), 2), 'Look up BusinessUnit from BusinessUnitID with XLOOKUP or INDEX/MATCH, then SUMIFS(Debit, BusinessUnit, "' + b + '").',
            [(m[m.BusinessUnit == b].Amount.sum(), "You summed Amount, which nets debits and credits (≈ 0 for balanced entries). Sum the Debit column.")], 90)
    for cls in coa.AccountClass.dropna().unique():
        x = m[m.AccountClass == cls]
        if len(x) < 5:
            continue
        add('journal', 'Excel', ['lookup', 'conditional sum'], f'Journal entries (Case 4): what is the net Amount posted to accounts in AccountClass "{cls}"? Round to two decimals.',
            num(x.Amount.sum(), 2), 'Look up AccountClass from GLAccountNumber in ChartOfAccounts (INDEX/MATCH or XLOOKUP), then SUMIFS(Amount, AccountClass, "' + cls + '").',
            [(x.Debit.sum(), "You summed debits only. Net amount = debits − credits, i.e. the Amount column.")], 120)
    for pid, bid, nm in prep[['PreparerID', 'BusinessUnitID', 'nm']].itertuples(index=False):
        x = m[m.nm == nm]
        if len(x) < 5:
            continue
        wrong = m[m.nm_v == nm]
        add('journal', 'Excel', ['two-key lookup', 'conditional sum'], f'Journal entries (Case 4): what is the total debit amount of lines prepared by {nm}? Round to two decimals.',
            num(x.Debit.sum(), 2), 'PreparerID is not unique: a preparer is identified by PreparerID AND BusinessUnitID. Use a two-condition lookup, e.g. =INDEX(PreparerName, MATCH(1,(PreparerID=D2)*(BusinessUnitID=C2),0)) or XLOOKUP(D2&C2, PreparerID&BusinessUnitID, PreparerName). Then SUMIFS on Debit.',
            [(wrong.Debit.sum() if len(wrong) else None, "You looked up the preparer with VLOOKUP on PreparerID only. Each PreparerID is used in several business units, so VLOOKUP always returns the first name. Match on PreparerID AND BusinessUnitID.")], 150)
    for s_ in src.Source.dropna().unique()[:8]:
        x = m[m.Source == s_]
        if len(x) < 5:
            continue
        add('journal', 'Excel', ['lookup', 'count'], f'Journal entries (Case 4): how many distinct journal entries (JENumber) come from source "{s_}"?',
            num(x.JENumber.nunique()), 'Look up Source from SourceID, then count unique JENumber values for that source (pivot table with distinct count, or =COUNTA(UNIQUE(FILTER(JENumber,Source="' + s_ + '")))).',
            [(len(x), "You counted journal entry LINES. Each entry has at least two lines (debit and credit) — count distinct JENumbers.")], 90)

# ---------------------------------------------------------------- restaurant regression (Excel)
def restaurant():
    sales = pd.read_excel(P['rest'], sheet_name='salesData')
    w = pd.read_excel(P['rest'], sheet_name='weatherData')
    g = pd.read_excel(P['rest'], sheet_name='gameData')
    d = sales.groupby('date').agg(sales=('netTotal', 'sum'), sales364=('netTotal_364', 'sum')).reset_index()
    d = d.merge(w, on='date', how='left').merge(g[['date', 'homeGame', 'gameDay']], on='date', how='left')
    d[['homeGame', 'gameDay']] = d[['homeGame', 'gameDay']].fillna(0)
    item = sales.merge(w, on='date', how='left').merge(g[['date', 'gameDay']], on='date', how='left').fillna({'gameDay': 0})
    import statsmodels.api as sm
    def ols(df, y, xs):
        X = sm.add_constant(df[xs].astype(float)); return sm.OLS(df[y].astype(float), X, missing='drop').fit()
    REST = {}
    sol_merge = 'Aggregate salesData to one row per date (pivot table: sum of netTotal and netTotal_364), look up tmax/prcp from weatherData and gameDay from gameData (blank = 0), then Data > Data Analysis > Regression.'
    ITEM = "You ran the regression on the item-level rows (one row per menu item per day). Aggregate sales to one row per day first — the question is about total daily sales."
    for xs, label in [(['tmax'], 'maximum temperature (tmax)'), (['gameDay'], 'gameDay'), (['sales364'], 'sales one year ago (sum of netTotal_364)'), (['prcp'], 'precipitation (prcp)')]:
        f = ols(d, 'sales', xs)
        alt = None
        if xs[0] in item.columns:
            alt = ols(item, 'netTotal', xs).params[xs[0]]
        add('restaurant', 'Excel', ['ETL merge', 'regression'], f'Restaurant case: regress total daily sales (sum of netTotal) on {label}. What is the slope coefficient? Round to two decimals.',
            num(f.params[xs[0]], 2), sol_merge, [(alt, ITEM), (f.params['const'], "That is the intercept, not the slope.")], 180)
        add('restaurant', 'Excel', ['regression', 'interpretation'], f'Restaurant case: in the regression of total daily sales on {label}, what is the p-value of the slope? Round to three decimals.',
            num(f.pvalues[xs[0]], 3), sol_merge + ' Read the P-value column of the coefficient row.', [], 180)
        REST[xs[0]] = f
    f = ols(d, 'sales', ['tmax'])
    add('restaurant', 'Excel', ['regression', 'fit'], 'Restaurant case: in the regression of total daily sales on tmax, what is R-squared? Round to three decimals.',
        num(f.rsquared, 3), sol_merge, [(ols(item, 'netTotal', ['tmax']).rsquared, ITEM), (f.rsquared_adj, "That is adjusted R-squared.")], 180)
    d['inter'] = d.sales364 * d.gameDay
    f = ols(d, 'sales', ['sales364', 'gameDay', 'inter'])
    add('restaurant', 'Excel', ['ETL merge', 'regression', 'interaction'], 'Restaurant case: regress total daily sales on sales one year ago, gameDay and their interaction (sales364 × gameDay). What is the interaction coefficient? Round to three decimals.',
        num(f.params['inter'], 3), sol_merge + ' Create the interaction column =sales364*gameDay before running the regression.', [], 240)
    last = d.date.max()
    f = ols(d, 'sales', ['sales364'])
    target = last + pd.Timedelta(days=7)
    s364 = sales[sales.date == target - pd.Timedelta(days=364)].netTotal.sum()
    # sales364 for the target day = sales on target-364 (if inside data)
    if s364 > 0:
        pred = f.params['const'] + f.params['sales364'] * s364
        add('restaurant', 'Excel', ['regression', 'prediction'], f'Restaurant case: the last day in the data is {last:%d %B %Y}. Using a regression of total daily sales on sales one year ago, predict total sales 7 days after the last day. Round to the nearest whole number.',
            num(pred, 0), f'Regress daily sales on sales364. The target day is {target:%d %B %Y}; its "sales one year ago" is total sales on {target - pd.Timedelta(days=364):%d %B %Y} = {s364:,.0f}. Prediction = intercept + slope × {s364:,.0f}.', [], 240)
    return d

# ---------------------------------------------------------------- SQL datasets
def sql_q(dbkey, path, skills, text, sql, check_fn, mistakes_sql=(), secs=90, source=None, chk=None):
    con = sqlite3.connect(path)
    val = con.execute(sql).fetchone()[0]
    ms = []
    for msql, why in mistakes_sql:
        try:
            ms.append((con.execute(msql).fetchone()[0], why))
        except Exception as e:
            print('mistake sql failed', e, msql, file=sys.stderr)
    con.close()
    add(dbkey, 'SQL', skills, text, check_fn(val), sql, ms, secs, source)

def chinook():
    p = P['chinook']
    con = sqlite3.connect(p)
    sql_q('chinook', p, ['count', 'filter'], 'How many invoices have totals greater than $10 and less than $20?',
          'SELECT COUNT(*) FROM Invoice WHERE Total > 10 AND Total < 20;', num,
          [('SELECT COUNT(*) FROM Invoice WHERE Total BETWEEN 10 AND 20;', 'BETWEEN includes the end points. "Greater than 10 and less than 20" excludes them.')], 45, 'PwC SQL')
    sql_q('chinook', p, ['filter', 'IN'], 'How many invoices are from customers in Brazil, Argentina or Chile (billing country)?',
          "SELECT COUNT(*) FROM Invoice WHERE BillingCountry IN ('Brazil','Argentina','Chile');", num, [], 45, 'PwC SQL')
    sql_q('chinook', p, ['LIKE'], 'How many invoices have a billing country that starts with "C"?',
          "SELECT COUNT(*) FROM Invoice WHERE BillingCountry LIKE 'C%';", num,
          [("SELECT COUNT(*) FROM Invoice WHERE BillingCountry LIKE '%C%';", "'%C%' matches C anywhere in the name. Use 'C%' for names that start with C.")], 45, 'PwC SQL')
    sql_q('chinook', p, ['NULL'], 'How many customers list their company?',
          'SELECT COUNT(Company) FROM Customer;', num,
          [('SELECT COUNT(*) FROM Customer;', 'COUNT(*) counts every customer. COUNT(Company) skips NULLs — or use WHERE Company IS NOT NULL.')], 45, 'PwC SQL')
    sql_q('chinook', p, ['text functions'], 'How long is the longest employee last name (number of characters)?',
          'SELECT MAX(LENGTH(LastName)) FROM Employee;', num, [], 45, 'PwC SQL')
    sql_q('chinook', p, ['DISTINCT'], 'How many distinct track prices appear in InvoiceLine?',
          'SELECT COUNT(DISTINCT UnitPrice) FROM InvoiceLine;', num,
          [('SELECT COUNT(UnitPrice) FROM InvoiceLine;', 'You counted all rows. Add DISTINCT.')], 45, 'PwC SQL')
    sql_q('chinook', p, ['dates'], 'How many employees were born on a Sunday?',
          "SELECT COUNT(*) FROM Employee WHERE strftime('%w', BirthDate) = '0';", num,
          [("SELECT COUNT(*) FROM Employee WHERE strftime('%w', BirthDate) = '7';", "In SQLite strftime('%w') returns 0 for Sunday (0–6), not 7.")], 75, 'PwC SQL')
    # parameterised
    countries = [r[0] for r in con.execute('SELECT BillingCountry FROM Invoice GROUP BY 1 HAVING COUNT(*) >= 7 ORDER BY COUNT(*) DESC LIMIT 12')]
    for c in countries:
        sql_q('chinook', p, ['filter', 'aggregate'], f'What is the total value of invoices billed to {c}? Round to two decimals.',
              f"SELECT ROUND(SUM(Total), 2) FROM Invoice WHERE BillingCountry = '{c}';", lambda v: num(v, 2),
              [(f"SELECT COUNT(*) FROM Invoice WHERE BillingCountry = '{c}';", 'You counted invoices. Use SUM(Total) for the value.'),
               (f"SELECT SUM(il.UnitPrice) FROM InvoiceLine il JOIN Invoice i USING(InvoiceId) JOIN Customer c ON c.CustomerId=i.CustomerId WHERE c.Country = '{c}';", 'You used the customer country. That gives the same here only if billing and customer country match — check you used BillingCountry.')], 60)
        sql_q('chinook', p, ['JOIN', 'count'], f'How many tracks (invoice lines) were bought by customers billed in {c}?',
              f"SELECT COUNT(*) FROM InvoiceLine il JOIN Invoice i ON i.InvoiceId = il.InvoiceId WHERE i.BillingCountry = '{c}';", num,
              [(f"SELECT COUNT(*) FROM Invoice WHERE BillingCountry = '{c}';", 'You counted invoices, not invoice lines. Join InvoiceLine to Invoice and count the lines.')], 90)
    genres = [r[0] for r in con.execute('SELECT g.Name FROM Genre g JOIN Track t USING(GenreId) GROUP BY 1 HAVING COUNT(*) >= 40 ORDER BY COUNT(*) DESC')]
    for gname in genres:
        sql_q('chinook', p, ['JOIN', 'count'], f'How many tracks in the {gname} genre have been downloaded (count invoice lines)?',
              f"SELECT COUNT(*) FROM InvoiceLine il JOIN Track t ON t.TrackId = il.TrackId JOIN Genre g ON g.GenreId = t.GenreId WHERE g.Name = '{gname}';", num,
              [(f"SELECT COUNT(*) FROM Track t JOIN Genre g ON g.GenreId = t.GenreId WHERE g.Name = '{gname}';", 'You counted tracks in the catalogue. Downloads are rows in InvoiceLine — join InvoiceLine → Track → Genre.'),
               (f"SELECT COUNT(DISTINCT il.TrackId) FROM InvoiceLine il JOIN Track t ON t.TrackId = il.TrackId JOIN Genre g ON g.GenreId = t.GenreId WHERE g.Name = '{gname}';", 'You counted distinct tracks. A track downloaded twice counts as two downloads.')], 120)
        sql_q('chinook', p, ['JOIN', 'aggregate'], f'What is the total revenue (UnitPrice × Quantity) from {gname} tracks? Round to two decimals.',
              f"SELECT ROUND(SUM(il.UnitPrice * il.Quantity), 2) FROM InvoiceLine il JOIN Track t ON t.TrackId = il.TrackId JOIN Genre g ON g.GenreId = t.GenreId WHERE g.Name = '{gname}';", lambda v: num(v, 2),
              [(f"SELECT SUM(t.UnitPrice) FROM Track t JOIN Genre g ON g.GenreId = t.GenreId WHERE g.Name = '{gname}';", 'You summed catalogue prices of all tracks in the genre. Revenue comes from InvoiceLine.')], 120)
    for y in range(2009, 2014):
        sql_q('chinook', p, ['dates', 'aggregate'], f'What was the total invoice value in {y}? Round to two decimals.',
              f"SELECT ROUND(SUM(Total), 2) FROM Invoice WHERE strftime('%Y', InvoiceDate) = '{y}';", lambda v: num(v, 2),
              [(f"SELECT COUNT(*) FROM Invoice WHERE strftime('%Y', InvoiceDate) = '{y}';", 'You counted invoices instead of summing Total.')], 75)
    for (eid, fn, ln) in con.execute("SELECT EmployeeId, FirstName, LastName FROM Employee WHERE Title LIKE '%Support Agent%'"):
        sql_q('chinook', p, ['JOIN', 'aggregate'], f'What is the total value of invoices from customers whose support rep is {fn} {ln}? Round to two decimals.',
              f"SELECT ROUND(SUM(i.Total), 2) FROM Invoice i JOIN Customer c ON c.CustomerId = i.CustomerId WHERE c.SupportRepId = {eid};", lambda v: num(v, 2),
              [(f"SELECT COUNT(*) FROM Customer WHERE SupportRepId = {eid};", 'You counted customers. Join Invoice to Customer and sum Total.')], 120)
    con.close()

def songs():
    p = P['songs']
    sql_q('songs', p, ['filter'], 'How many songs have danceability, energy and valence all greater than 0.6?',
          'SELECT COUNT(*) FROM songs WHERE danceability > 0.6 AND energy > 0.6 AND valence > 0.6;', num,
          [('SELECT COUNT(*) FROM songs WHERE danceability > 0.6 OR energy > 0.6 OR valence > 0.6;', 'You used OR. All three conditions must hold — use AND.')], 45, 'CS50 songs')
    sql_q('songs', p, ['aggregate'], 'What is the average tempo of all songs? Round to two decimals.',
          'SELECT ROUND(AVG(tempo), 2) FROM songs;', lambda v: num(v, 2), [], 30, 'CS50 songs')
    sql_q('songs', p, ['LIKE'], 'How many songs feature other artists ("feat." in the song name)?',
          "SELECT COUNT(*) FROM songs WHERE name LIKE '%feat.%';", num, [], 30, 'CS50 songs')
    con = sqlite3.connect(p)
    arts = [r[0] for r in con.execute('SELECT a.name FROM artists a JOIN songs s ON s.artist_id = a.id GROUP BY a.id HAVING COUNT(*) >= 2 ORDER BY COUNT(*) DESC')]
    con.close()
    for a in arts:
        q = a.replace("'", "''")
        sql_q('songs', p, ['JOIN', 'aggregate'], f'What is the average energy of songs by {a}? Round to three decimals.',
              f"SELECT ROUND(AVG(energy), 3) FROM songs WHERE artist_id = (SELECT id FROM artists WHERE name = '{q}');", lambda v: num(v, 3),
              [("SELECT AVG(energy) FROM songs;", 'You averaged over all songs — filter on the artist (subquery or JOIN on artists).')], 60, 'CS50 songs')
        sql_q('songs', p, ['JOIN', 'count'], f'How many songs by {a} are in the database?',
              f"SELECT COUNT(*) FROM songs s JOIN artists a ON a.id = s.artist_id WHERE a.name = '{q}';", num, [], 45)

def movies():
    p = P['movies']
    con = sqlite3.connect(p)
    for y in range(2005, 2020):
        sql_q('movies', p, ['filter', 'count'], f'How many movies in the practice database were released in {y}?',
              f'SELECT COUNT(*) FROM movies WHERE year = {y};', num,
              [(f'SELECT COUNT(*) FROM movies WHERE year >= {y};', f'You used >=. "Released in {y}" means year = {y}.')], 30)
        sql_q('movies', p, ['JOIN', 'aggregate'], f'What is the average rating of movies released in {y}? Round to two decimals.',
              f'SELECT ROUND(AVG(r.rating), 2) FROM movies m JOIN ratings r ON r.movie_id = m.id WHERE m.year = {y};', lambda v: num(v, 2),
              [('SELECT AVG(rating) FROM ratings;', f'You averaged all ratings — join to movies and filter year = {y}.')], 75)
    people = ['Johnny Depp', 'Helena Bonham Carter', 'Tom Hanks', 'Leonardo DiCaprio', 'Scarlett Johansson', 'Brad Pitt', 'Meryl Streep', 'Samuel L. Jackson', 'Morgan Freeman', 'Natalie Portman', 'Denzel Washington', 'Christian Bale']
    for n in people:
        ids = con.execute('SELECT id FROM people WHERE name = ?', (n,)).fetchall()
        if len(ids) != 1:
            continue
        sql_q('movies', p, ['JOIN', 'count'], f'In how many movies in the practice database did {n} star?',
              f"SELECT COUNT(*) FROM stars s JOIN people p ON p.id = s.person_id WHERE p.name = '{n}';", num, [], 60)
        sql_q('movies', p, ['JOIN', 'aggregate'], f'What is the average rating of movies starring {n}? Round to two decimals.',
              f"SELECT ROUND(AVG(r.rating), 2) FROM ratings r JOIN stars s ON s.movie_id = r.movie_id JOIN people p ON p.id = s.person_id WHERE p.name = '{n}';", lambda v: num(v, 2), [], 90)
        sql_q('movies', p, ['filter'], f'In what year was {n} born?',
              f"SELECT birth FROM people WHERE name = '{n}';", num, [], 30)
    sql_q('movies', p, ['JOIN', 'subquery'], 'How many different people starred in a movie with Kevin Bacon (born 1958), excluding Kevin Bacon himself?',
          "SELECT COUNT(DISTINCT s.person_id) FROM stars s WHERE s.movie_id IN (SELECT movie_id FROM stars WHERE person_id = (SELECT id FROM people WHERE name = 'Kevin Bacon' AND birth = 1958)) AND s.person_id != (SELECT id FROM people WHERE name = 'Kevin Bacon' AND birth = 1958);", num,
          [("SELECT COUNT(DISTINCT s.person_id) FROM stars s WHERE s.movie_id IN (SELECT movie_id FROM stars WHERE person_id = (SELECT id FROM people WHERE name = 'Kevin Bacon' AND birth = 1958));", 'You included Kevin Bacon himself.'),
           ("SELECT COUNT(s.person_id) FROM stars s WHERE s.movie_id IN (SELECT movie_id FROM stars WHERE person_id = (SELECT id FROM people WHERE name = 'Kevin Bacon' AND birth = 1958)) AND s.person_id != (SELECT id FROM people WHERE name = 'Kevin Bacon' AND birth = 1958);", 'You forgot DISTINCT — people who acted with him twice are counted twice.')], 180, 'CS50 movies')
    sql_q('movies', p, ['JOIN', 'DISTINCT'], 'How many different people directed a movie with a rating of at least 9.0?',
          'SELECT COUNT(DISTINCT d.person_id) FROM directors d JOIN ratings r ON r.movie_id = d.movie_id WHERE r.rating >= 9.0;', num,
          [('SELECT COUNT(*) FROM directors d JOIN ratings r ON r.movie_id = d.movie_id WHERE r.rating >= 9.0;', 'Add DISTINCT — a director with two such movies counts once.'),
           ('SELECT COUNT(DISTINCT d.person_id) FROM directors d JOIN ratings r ON r.movie_id = d.movie_id WHERE r.rating > 9.0;', '"At least 9.0" means >= 9.0.')], 120, 'CS50 movies')
    con.close()

def pcards():
    p = P['pcards']
    T = 'pcards'
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    pm = "CAST(substr(PostedDate, 1, instr(PostedDate, '/') - 1) AS INTEGER)"
    POST = "You used the month of PostedDate. The case says: for all date questions use TransactionDate (the Month column is already derived from it)."
    for i, mn in enumerate(months, 1):
        sql_q('pcards', p, ['filter', 'count'], f'How many P-card transactions took place in {mn} 2014 (by TransactionDate)?',
              f'SELECT COUNT(*) FROM {T} WHERE Year = 2014 AND Month = {i};', num,
              [(f'SELECT COUNT(*) FROM {T} WHERE {pm} = {i};', POST),
               (f'SELECT COUNT(*) FROM {T} WHERE Month = {i} AND Amount > 0;', 'You excluded returns (negative amounts). The question asks for all transactions.')], 45)
        sql_q('pcards', p, ['filter', 'aggregate'], f'What is the total dollar amount of returns (negative amounts) in {mn} 2014? Give the amount as a negative number, rounded to two decimals.',
              f'SELECT ROUND(SUM(Amount), 2) FROM {T} WHERE Month = {i} AND Amount < 0;', lambda v: num(v, 2),
              [(f'SELECT -SUM(Amount) FROM {T} WHERE Month = {i} AND Amount < 0;', 'Right size, wrong sign — returns are negative amounts; report them as negative.'),
               (f'SELECT SUM(Amount) FROM {T} WHERE {pm} = {i} AND Amount < 0;', POST),
               (f'SELECT COUNT(*) FROM {T} WHERE Month = {i} AND Amount < 0;', 'You counted returns. The question asks for the dollar total: SUM(Amount).')], 60)
        sql_q('pcards', p, ['filter', 'count'], f'How many transactions in {mn} 2014 were for more than $3,000?',
              f'SELECT COUNT(*) FROM {T} WHERE Month = {i} AND Amount > 3000;', num,
              [(f'SELECT COUNT(*) FROM {T} WHERE Month = {i} AND Amount >= 3000;', '"More than" means > 3000, not >= 3000.'),
               (f'SELECT COUNT(*) FROM {T} WHERE {pm} = {i} AND Amount > 3000;', POST)], 45)
        sql_q('pcards', p, ['calculated field', 'aggregate'], f'If OSU had paid 4.5% sales tax on its purchases in {mn} 2014, how much tax would it have paid? Ignore returns. Round to two decimals.',
              f'SELECT ROUND(SUM(Amount * 0.045), 2) FROM {T} WHERE Month = {i} AND Amount > 0;', lambda v: num(v, 2),
              [(f'SELECT SUM(Amount * 0.045) FROM {T} WHERE Month = {i};', 'You included returns. Filter Amount > 0.'),
               (f'SELECT SUM(Amount * 0.45) FROM {T} WHERE Month = {i} AND Amount > 0;', '4.5% = 0.045, not 0.45.'),
               (f'SELECT SUM(Amount * 4.5) FROM {T} WHERE Month = {i} AND Amount > 0;', '4.5% = 0.045, not 4.5.')], 75)
    sql_q('pcards', p, ['count'], 'How many P-card transactions are in the 2014 practice database? (Label the column TotalTrans.)',
          f'SELECT COUNT(*) AS TotalTrans FROM {T};', num, [], 30, 'P-card Task 4 Q5')
    sql_q('pcards', p, ['filter', 'count'], 'How many 2014 transactions are for $5,000 or more? (TotalTransGT5k)',
          f'SELECT COUNT(*) AS TotalTransGT5k FROM {T} WHERE Amount >= 5000;', num,
          [(f'SELECT COUNT(*) FROM {T} WHERE Amount > 5000;', '"More than or equal to" — use >= 5000.')], 45, 'P-card Task 4 Q6')
    sql_q('pcards', p, ['filter', 'aggregate'], 'What is the total dollar amount of returns from January to March 2014, inclusive? Round to two decimals (negative number).',
          f'SELECT ROUND(SUM(Amount), 2) FROM {T} WHERE Month BETWEEN 1 AND 3 AND Amount < 0;', lambda v: num(v, 2),
          [(f'SELECT SUM(Amount) FROM {T} WHERE Month BETWEEN 1 AND 2 AND Amount < 0;', 'Inclusive means March is included.'),
           (f'SELECT SUM(Amount) FROM {T} WHERE Month < 3 AND Amount < 0;', 'Inclusive means March is included (Month <= 3).')], 60, 'P-card Task 4 Q7')
    con = sqlite3.connect(p)
    top = con.execute(f'SELECT FullName, COUNT(*) FROM {T} GROUP BY CardholderFirstInitial, CardholderLastName ORDER BY 2 DESC LIMIT 1').fetchone()
    toplast = con.execute(f'SELECT CardholderLastName FROM {T} GROUP BY CardholderLastName ORDER BY COUNT(*) DESC LIMIT 1').fetchone()[0]
    add('pcards', 'SQL', ['GROUP BY', 'ranking'], 'Which cardholder (first initial + last name, e.g. "G Thacker") had the most transactions in 2014?',
        txt(top[0]), f"SELECT CardholderFirstInitial || ' ' || CardholderLastName AS Name, COUNT(*) AS NumTrans FROM {T} GROUP BY CardholderFirstInitial, CardholderLastName ORDER BY NumTrans DESC LIMIT 1;",
        [], 75, 'P-card Task 4 Q9')
    sql_q('pcards', p, ['GROUP BY', 'ranking'], 'How many transactions did the most active cardholder make in 2014?',
          f'SELECT MAX(n) FROM (SELECT COUNT(*) AS n FROM {T} GROUP BY CardholderFirstInitial, CardholderLastName);', num,
          [(f'SELECT MAX(n) FROM (SELECT COUNT(*) AS n FROM {T} GROUP BY CardholderLastName);', 'You grouped by last name only. The case says a person = first initial + last name.')], 75, 'P-card Task 4 Q9')
    sql_q('pcards', p, ['GROUP BY', 'HAVING'], 'How many cardholders made more than 10 transactions in 2014?',
          f'SELECT COUNT(*) FROM (SELECT 1 FROM {T} GROUP BY CardholderFirstInitial, CardholderLastName HAVING COUNT(*) > 10);', num,
          [(f'SELECT COUNT(*) FROM (SELECT 1 FROM {T} GROUP BY CardholderFirstInitial, CardholderLastName HAVING COUNT(*) >= 10);', '"More than 10" is HAVING COUNT(*) > 10.'),
           (f'SELECT COUNT(*) FROM (SELECT 1 FROM {T} GROUP BY CardholderLastName HAVING COUNT(*) > 10);', 'You grouped by last name only — use first initial + last name.')], 90, 'P-card Task 4 Q11')
    sql_q('pcards', p, ['GROUP BY', 'HAVING'], 'How many cardholders returned more than $1,000 of goods in 2014?',
          f'SELECT COUNT(*) FROM (SELECT 1 FROM {T} WHERE Amount < 0 GROUP BY CardholderFirstInitial, CardholderLastName HAVING -SUM(Amount) > 1000);', num,
          [(f'SELECT COUNT(*) FROM (SELECT 1 FROM {T} WHERE Amount < 0 GROUP BY CardholderFirstInitial, CardholderLastName HAVING SUM(Amount) > 1000);', 'Returns are negative, so SUM(Amount) > 1000 is never true. Use -SUM(Amount) > 1000 or SUM(Amount) < -1000.')], 120, 'P-card Task 4 Q12')
    sql_q('pcards', p, ['control test', 'GROUP BY'], 'Control test: how many cardholders spent more than $50,000 in total in 2014?',
          f'SELECT COUNT(*) FROM (SELECT 1 FROM {T} GROUP BY CardholderFirstInitial, CardholderLastName HAVING SUM(Amount) > 50000);', num, [], 90, 'P-card Task 5 Q1')
    sql_q('pcards', p, ['control test', 'GROUP BY'], 'Control test: how many cardholder-months in 2014 had total spending above $10,000?',
          f'SELECT COUNT(*) FROM (SELECT 1 FROM {T} GROUP BY CardholderFirstInitial, CardholderLastName, Month HAVING SUM(Amount) > 10000);', num,
          [(f'SELECT COUNT(*) FROM (SELECT 1 FROM {T} GROUP BY CardholderFirstInitial, CardholderLastName HAVING SUM(Amount) > 10000);', 'You grouped by person only — the limit is per month, so group by person AND Month.')], 120, 'P-card Task 5 Q2')
    sql_q('pcards', p, ['control test', 'filter'], 'Control test: how many 2014 transactions exceed the single-transaction limit of $5,000?',
          f'SELECT COUNT(*) FROM {T} WHERE Amount > 5000;', num,
          [(f'SELECT COUNT(*) FROM {T} WHERE Amount >= 5000;', 'A $5,000 transaction is within the limit ("shall not exceed") — use > 5000.')], 45, 'P-card Task 5 Q3')
    sql_q('pcards', p, ['forensic', 'GROUP BY'], 'Forensic test: how many groups of possible duplicate payments are there in 2014 (same day, same vendor, same cardholder, same amount, more than one charge, returns excluded)?',
          f'SELECT COUNT(*) FROM (SELECT 1 FROM {T} WHERE Amount > 0 GROUP BY TransactionDate, Vendor, CardholderFirstInitial, CardholderLastName, Amount HAVING COUNT(*) > 1);', num,
          [(f'SELECT COUNT(*) FROM (SELECT 1 FROM {T} GROUP BY TransactionDate, Vendor, CardholderFirstInitial, CardholderLastName, Amount HAVING COUNT(*) > 1);', 'You did not exclude returns (Amount > 0).')], 150, 'P-card Task 7 Q2')
    sql_q('pcards', p, ['forensic', 'filter'], 'Forensic test: how many 2014 transactions are four-digit whole-dollar amounts ending in 000 (e.g. 2000.00)?',
          f'SELECT COUNT(*) FROM {T} WHERE Amount >= 1000 AND Amount < 10000 AND Amount = CAST(Amount AS INTEGER) AND CAST(Amount AS INTEGER) % 1000 = 0;', num,
          [(f'SELECT COUNT(*) FROM {T} WHERE CAST(Amount AS INTEGER) % 1000 = 0 AND Amount >= 1000 AND Amount < 10000;', 'You ignored the cents — 2000.50 is not a round amount. Require Amount = CAST(Amount AS INTEGER).')], 150, 'P-card Task 7 Q4')
    sql_q('pcards', p, ['forensic', 'Benford'], "Benford's test: what percentage of 2014 transactions of at least $1.00 have a first digit of 1? Round to three decimals (e.g. 30.103).",
          f"SELECT ROUND(100.0 * SUM(substr(CAST(Amount AS TEXT),1,1) = '1') / COUNT(*), 3) FROM {T} WHERE Amount >= 1;", lambda v: num(v, 3, pct=True),
          [(f"SELECT 100.0 * SUM(substr(CAST(ABS(Amount) AS TEXT),1,1) = '1') / COUNT(*) FROM {T} WHERE ABS(Amount) >= 1;", 'You included returns (negative amounts). The case analyses transactions of at least 1.00.'),
           (f"SELECT 100.0 * SUM(substr(CAST(Amount AS TEXT),1,1) = '1') / COUNT(*) FROM {T};", 'You did not exclude amounts below 1.00 (and negatives).')], 150, 'P-card Task 7 Q1')
    sql_q('pcards', p, ['CASE', 'aggregate'], 'Amazon smile: OSU earns 0.75% on Amazon.com transactions of $500 or more and 0.50% on smaller ones. How much would OSU have earned in 2014 on the vendor written exactly "Amazon.com" (positive amounts only)? Round to two decimals.',
          f"SELECT ROUND(SUM(CASE WHEN Amount >= 500 THEN Amount * 0.0075 ELSE Amount * 0.005 END), 2) FROM {T} WHERE Vendor = 'Amazon.com' AND Amount > 0;", lambda v: num(v, 2),
          [(f"SELECT SUM(CASE WHEN Amount > 500 THEN Amount * 0.0075 ELSE Amount * 0.005 END) FROM {T} WHERE Vendor = 'Amazon.com' AND Amount > 0;", '"$500 and more" includes 500: use >= 500.'),
           (f"SELECT SUM(CASE WHEN Amount >= 500 THEN Amount * 0.0075 ELSE Amount * 0.005 END) FROM {T} WHERE Vendor LIKE 'Amazon.com' AND Amount > 0;", "In SQLite, LIKE ignores upper/lower case, so it also picked up the vendor 'AMAZON.COM'. Use = 'Amazon.com' for an exact match."),
           (f"SELECT SUM(CASE WHEN Amount >= 500 THEN Amount * 0.0075 ELSE Amount * 0.005 END) FROM {T} WHERE Vendor LIKE '%AMAZON%' AND Amount > 0;", "LIKE '%AMAZON%' also catches AMAZON MKTPLACE PMTS, Kindle, Prime and other Amazon vendors."),
           (f"SELECT SUM(CASE WHEN Amount >= 500 THEN Amount * 0.0075 ELSE Amount * 0.005 END) FROM {T} WHERE Vendor = 'Amazon.com';", 'You included returns — use Amount > 0.')], 150, 'P-card Task 4 Q16')
    for i, mn in enumerate(months, 1):
        if i not in (3, 6, 9, 11, 12):
            continue
        sql_q('pcards', p, ['date arithmetic', 'aggregate'], f'For transactions in {mn} 2014, what is the average number of days between TransactionDate and PostedDate? Round to two decimals.',
              f"""SELECT ROUND(AVG(julianday(printf('%04d-%02d-%02d', CAST(substr(PostedDate, instr(substr(PostedDate, instr(PostedDate,'/')+1),'/') + instr(PostedDate,'/') + 1, 4) AS INT), CAST(substr(PostedDate,1,instr(PostedDate,'/')-1) AS INT), CAST(substr(PostedDate, instr(PostedDate,'/')+1, instr(substr(PostedDate, instr(PostedDate,'/')+1),'/')-1) AS INT)))
 - julianday(printf('%04d-%02d-%02d', CAST(substr(TransactionDate, instr(substr(TransactionDate, instr(TransactionDate,'/')+1),'/') + instr(TransactionDate,'/') + 1, 4) AS INT), CAST(substr(TransactionDate,1,instr(TransactionDate,'/')-1) AS INT), CAST(substr(TransactionDate, instr(TransactionDate,'/')+1, instr(substr(TransactionDate, instr(TransactionDate,'/')+1),'/')-1) AS INT)))), 2)
FROM {T} WHERE Month = {i};""", lambda v: num(v, 2), [], 240, 'P-card Task 4 Q15')
    con.close()

# ---------------------------------------------------------------- data interpretation exams (restaurant regressions)
def interpretation(d):
    import statsmodels.api as sm
    d = d.copy()
    d['weekend'] = d.date.dt.dayofweek.isin([5, 6]).astype(int)
    d['inter'] = d.sales364 * d.gameDay
    specs = [
        ('Temperature', ['tmax'], {'tmax': 'maximum temperature (°F)'}),
        ('Game day', ['gameDay'], {'gameDay': 'game day (1 = football game that day, 0 = no game; reference group)'}),
        ('Weather', ['tmax', 'prcp'], {'tmax': 'maximum temperature (°F)', 'prcp': 'precipitation (inches)'}),
        ('Last year and game day', ['sales364', 'gameDay'], {'sales364': 'sales on the same weekday one year earlier (USD)', 'gameDay': 'game day (1 = game, 0 = no game)'}),
        ('Interaction', ['sales364', 'gameDay', 'inter'], {'sales364': 'sales one year earlier (USD)', 'gameDay': 'game day (1 = game, 0 = no game)', 'inter': 'sales one year earlier × game day'}),
        ('Weekend and weather', ['weekend', 'tmax', 'prcp'], {'weekend': 'weekend (1 = Saturday/Sunday, 0 = weekday)', 'tmax': 'maximum temperature (°F)', 'prcp': 'precipitation (inches)'}),
        ('Full model', ['sales364', 'tmax', 'prcp', 'gameDay'], {'sales364': 'sales one year earlier (USD)', 'tmax': 'maximum temperature (°F)', 'prcp': 'precipitation (inches)', 'gameDay': 'game day (1 = game, 0 = no game)'}),
    ]
    rng = random.Random(7)
    exams = []
    models = {}
    for name, xs, labels in specs:
        f = sm.OLS(d['sales'], sm.add_constant(d[xs].astype(float)), missing='drop').fit()
        models[name] = dict(xs=xs, labels=labels, params={k: float(v) for k, v in f.params.items()}, p={k: float(v) for k, v in f.pvalues.items()},
                            r2=float(f.rsquared), n=int(f.nobs), ranges={x: [float(d[x].min()), float(d[x].max())] for x in xs if x != 'inter'})
    def table(mname):
        m = models[mname]
        rows = [{'term': 'Intercept', 'name': 'b0', 'est': m['params']['const'], 'p': m['p']['const']}]
        for k, x in enumerate(m['xs'], 1):
            rows.append({'term': m['labels'][x].split(' (')[0], 'name': f'b{k}', 'est': m['params'][x], 'p': m['p'][x]})
        return rows
    def predict(m, vals):
        return m['params']['const'] + sum(m['params'][x] * vals[x] for x in m['xs'])
    eid = 0
    names = list(models)
    for rep in range(6):
        for mname in names:
            m = models[mname]
            eid += 1
            qs = []
            # Q1 prediction
            vals = {}
            for x in m['xs']:
                if x == 'inter':
                    continue
                lo, hi = m['ranges'][x]
                if x in ('gameDay', 'weekend'):
                    vals[x] = rng.choice([0, 1])
                elif x == 'prcp':
                    vals[x] = rng.choice([0, 0.2, 0.5, 1.0])
                elif x == 'tmax':
                    vals[x] = rng.choice(range(int(lo) + 10, int(hi) - 5, 5))
                else:
                    vals[x] = rng.choice(range(int(lo / 100) * 100 + 500, int(hi / 100) * 100 - 500, 100))
            if 'inter' in m['xs']:
                vals['inter'] = vals['sales364'] * vals['gameDay']
            pred = predict(m, vals)
            desc = ', '.join(f"{m['labels'][x].split(' (')[0]} = {vals[x]:g}" for x in m['xs'] if x != 'inter')
            wrong_noint = pred - (m['params']['inter'] * vals['inter'] if 'inter' in m['xs'] else 0)
            work = ' + '.join([f"{m['params']['const']:.2f}"] + [f"({m['params'][x]:.4f} × {vals[x]:g})" for x in m['xs']])
            qs.append(dict(kind='predict', text=f'Predict total daily sales (USD) for a day with {desc}. Round to the nearest whole dollar.',
                           check=num(round(pred), 0), mistakes=[{'value': round(m['params']['const']), 'why': 'That is just the intercept — add each coefficient × its value.'}] +
                           ([{'value': round(wrong_noint), 'why': 'You left out the interaction term (sales364 × gameDay). Multiply the two values and include b3 × that product.'}] if 'inter' in m['xs'] and vals['gameDay'] == 1 else []),
                           solution=f'Substitute the values into the model: {work} = {pred:,.2f}.'))
            # Q2 interpret a coefficient
            x = rng.choice([x for x in m['xs'] if x != 'inter'])
            b = m['params'][x]
            unit = {'tmax': 'one degree warmer maximum temperature', 'prcp': 'one more inch of precipitation', 'sales364': 'one dollar more in sales a year earlier',
                    'gameDay': 'a game day compared with a non-game day', 'weekend': 'a weekend day compared with a weekday'}[x]
            other = ' holding the other variables constant' if len(m['xs']) > 1 else ''
            if x == 'gameDay' and 'inter' in m['xs']:
                other = ' when sales one year earlier are 0 (because of the interaction term)'
            correct = f'{unit[0].upper() + unit[1:]} is associated with {abs(b):,.2f} USD {"higher" if b > 0 else "lower"} predicted daily sales{other}.'
            opts = [correct,
                    f'{unit[0].upper() + unit[1:]} is associated with {abs(b):,.2f} USD {"lower" if b > 0 else "higher"} predicted daily sales{other}.',
                    f'{unit[0].upper() + unit[1:]} is associated with {abs(b):,.2f}% {"higher" if b > 0 else "lower"} predicted daily sales{other}.',
                    f'{unit[0].upper() + unit[1:]} causes daily sales to change by exactly {b:,.2f} USD on every day.']
            rng.shuffle(opts)
            qs.append(dict(kind='interpret', text=f'Which statement correctly interprets the coefficient on {m["labels"][x].split(" (")[0]}?',
                           check=choice(opts, correct), mistakes=[], solution=f'The coefficient is {b:,.4f}. In a linear regression it is the change in the predicted outcome (USD of sales) for a one-unit change in the variable{other}. A regression on observational data shows association, not proof of causation.'))
            # Q3 significance
            x = rng.choice(m['xs'])
            pv = m['p'][x]
            lab = m['labels'][x].split(' (')[0]
            sig = pv < 0.05
            opts = ['Yes — the p-value is below 0.05, so the coefficient is statistically significant at the 5% level.',
                    'No — the p-value is above 0.05, so we cannot reject that the coefficient is zero at the 5% level.']
            qs.append(dict(kind='significance', text=f'At the 5% level, is the coefficient on {lab} statistically significant?',
                           check=choice(opts, opts[0] if sig else opts[1]), mistakes=[],
                           solution=f'The p-value for {lab} is {pv:.3f}, which is {"below" if sig else "above"} 0.05.'))
            # Q4 change / R2
            if 'gameDay' in m['xs'] and 'inter' in m['xs']:
                s = rng.choice(range(2000, 6000, 250))
                eff = m['params']['gameDay'] + m['params']['inter'] * s
                qs.append(dict(kind='effect', text=f'By how much does a game day change predicted sales on a day when sales one year earlier were {s:,} USD? Round to the nearest whole dollar.',
                               check=num(round(eff), 0), mistakes=[{'value': round(m['params']['gameDay']), 'why': 'You only used b2. With an interaction, the game-day effect = b2 + b3 × sales one year earlier.'}],
                               solution=f'Game-day effect = b2 + b3 × {s:,} = {m["params"]["gameDay"]:.2f} + {m["params"]["inter"]:.4f} × {s:,} = {eff:,.2f}.'))
            elif rng.random() < 0.5 and any(x not in ('gameDay', 'weekend') for x in m['xs']):
                x = rng.choice([x for x in m['xs'] if x not in ('gameDay', 'weekend')])
                step = {'tmax': 10, 'prcp': 0.5, 'sales364': 500}[x]
                eff = m['params'][x] * step
                qs.append(dict(kind='effect', text=f'How much does predicted daily sales change if {m["labels"][x].split(" (")[0]} increases by {step:g}{", other variables unchanged" if len(m["xs"]) > 1 else ""}? Round to the nearest whole dollar (use a minus sign for a decrease).',
                               check=num(round(eff), 0), mistakes=[{'value': round(m['params'][x]), 'why': f'That is the effect of a one-unit change. Multiply the coefficient by {step:g}.'}, {'value': round(-eff), 'why': 'Check the sign of the coefficient.'}],
                               solution=f'Change = coefficient × change in x = {m["params"][x]:.4f} × {step:g} = {eff:,.2f}.'))
            else:
                r2 = m['r2'] * 100
                qs.append(dict(kind='fit', text='What percentage of the variation in daily sales does the model explain? Give a percentage with one decimal.',
                               check=num(round(r2, 1), 1, pct=True), mistakes=[], solution=f'R² = {m["r2"]:.4f}, i.e. {r2:.1f}% of the variation in daily sales.'))
            exams.append(dict(id=f'REG{eid:03d}', model=mname, n=m['n'], r2=m['r2'], rows=table(mname),
                              equation='Predicted sales = ' + ' + '.join(['b0'] + [f'b{k}[{m["labels"][x].split(" (")[0]}]' for k, x in enumerate(m['xs'], 1)]),
                              vars=[{'name': m['labels'][x].split(' (')[0], 'desc': m['labels'][x]} for x in m['xs']], questions=qs))
    return exams

# ---------------------------------------------------------------- run
nyc(); payroll(); etl(); rest = restaurant(); chinook(); songs(); movies(); pcards()
for i, q in enumerate(QUESTIONS, 1):
    q['id'] = f'Q{i:03d}'
interp = interpretation(rest)

DATASETS = {
    'nyc': dict(name='NYC film permits', files=['NYC_Film_Permits.txt'], case='Excel Part 1 (PwC)'),
    'payroll15': dict(name='IntegrateCo payroll 2015', files=['IntegrateCo_2015payroll.csv', 'IntegrateCo_jobcodes.csv', 'IntegrateCo_locations.csv'], case='Excel Part 3 (IntegrateCo)'),
    'payroll16': dict(name='IntegrateCo payroll 2016', files=['IntegrateCo_2016payroll.csv', 'IntegrateCo_jobcodes.csv', 'IntegrateCo_locations.csv'], case='Excel Part 3 (IntegrateCo)'),
    'plants2': dict(name='Employee codes (ETL Case 2)', files=['ETL_Case2_Excel.xlsx'], case='Excel Part 2 (ETL)'),
    'plants3': dict(name='Messy employee codes (ETL Case 3)', files=['ETL_Case3_Excel.xlsx'], case='Excel Part 2 (ETL)'),
    'journal': dict(name='Journal entries (ETL Case 4)', files=['ETL_Case4_Excel.xlsx'], case='Excel Part 2 (ETL)'),
    'restaurant': dict(name='Restaurant sales', files=['restaurant_data.xlsm'], case='Excel Part 4 (Regression)'),
    'chinook': dict(name='Chinook music store', files=['Chinook_Sqlite.sqlite'], case='SQL Part 1 (PwC)'),
    'songs': dict(name='Songs', files=['songs.db'], case='SQL Part 1 (CS50)'),
    'movies': dict(name='Movies (practice subset)', files=['movies_subset.db'], case='SQL Part 1 (CS50)'),
    'pcards': dict(name='Purchasing cards 2014 (practice subset)', files=['pcards_2014.db'], case='SQL Part 2 (P-cards)'),
}
for k, v in DATASETS.items():
    v['count'] = sum(q['dataset'] == k for q in QUESTIONS)

# data-manipulation exams: 3 Excel questions from one dataset + 3 SQL questions from one database
rng = random.Random(42)
by = {}
for q in QUESTIONS:
    by.setdefault((q['tool'], q['dataset']), []).append(q['id'])
excel_ds = [k for k in by if k[0] == 'Excel' and len(by[k]) >= 6]
sql_ds = [k for k in by if k[0] == 'SQL' and len(by[k]) >= 6]
exams = []
for i in range(1, 201):
    e, s = rng.choice(excel_ds), rng.choice(sql_ds)
    qs = rng.sample(by[e], 3) + rng.sample(by[s], 3)
    secs = sum(next(q['secs'] for q in QUESTIONS if q['id'] == x) for x in qs)
    exams.append(dict(id=f'E{i:03d}', datasets=[e[1], s[1]], questions=qs, minutes=max(8, round(secs / 60))))

(OUT / 'data').mkdir(parents=True, exist_ok=True)
(OUT / 'data' / 'bank.js').write_text('window.BANK = ' + json.dumps(dict(questions=QUESTIONS, exams=exams, interp=interp, datasets=DATASETS), ensure_ascii=False) + ';\n')
print(len(QUESTIONS), 'questions;', sum(len(q['mistakes']) for q in QUESTIONS), 'diagnosed mistakes;', len(exams), 'exams;', len(interp), 'interpretation exams')
from collections import Counter
print(Counter((q['tool'], q['dataset']) for q in QUESTIONS))
