# Exam Practice: Data Analytics in Accounting

A practice website for the oral exam in *Data Analytics in Accounting* (SDU). It covers the data manipulation exam (Excel + SQL) and the data interpretation exam (regression). Everything is built only from the course cases and data files.

**What is on the site**
- **464 questions** on 11 course datasets: NYC film permits, IntegrateCo payroll 2015/2016, ETL cases 2–4 (employee codes, journal entries), the restaurant regression case, Chinook, CS50 songs and movies, and P-cards.
- **200 data manipulation exams.** Each has 3 Excel questions on one dataset and 3 SQL questions on one database, with a timer and file downloads.
- **42 data interpretation exams** built from regressions run on the restaurant data: predict, interpret a coefficient, test significance, and measure an effect or R².
- **Check my answer** (the new feature, described below).
- **My progress.** Solved questions and weak skills are stored in the browser only (localStorage). Nothing is sent anywhere.

## How it works
`tools/gen.py` reads the course files and computes every correct answer with pandas, SQLite and statsmodels. It also computes the value a student would get from each typical mistake. For every SQL question, the query shown as the worked solution is the same query that produced the answer. The script checks itself against the course solution keys: NYC permits `solutions.xlsx` and `PWC answers.docx` (for example 33,502 records, 193 student films, 60/49/77/10 invoices).

The site is plain HTML/CSS/JavaScript with no build step and no server, so it runs on GitHub Pages.

`files/` holds the downloads. `pcards.db` (94 MB) and `movies.db` (69 MB) exceed GitHub's 25 MB upload limit, so the site uses practice subsets made by `tools/make_subsets.py`: P-cards for calendar year 2014, and movies with at least 10,000 IMDb votes. All answers are computed on those subsets.

## Added functionality: *Check my answer* with mistake diagnosis

On the original site, the 400 data manipulation questions have no answer and no way to check one. The only help is an AI tutor. A student can spend ten minutes on a SUMIFS or a JOIN and still not know whether their number is right, and an LLM cannot reliably tell them either: it has not seen the data, and much of the original site's improvement list is about controlling AI cost, failures and truncation. On this site the student types the number they got, and it is checked instantly against a value computed from the actual data file. This is free, deterministic and works offline. If the number matches a mistake the site recognises, the student is told which one, for example:
- *"This is what you get when Excel reads the US dates with Danish regional settings."* This is a real trap for SDU students: `7/11/2016` becomes 7 November and `7/18/2016` stays text.
- *"You extracted the job code with MID(Job,3,3); codes like 14H002 drop out."*
- *"PreparerID is not unique; your VLOOKUP returned the first name."*
- *"You did not exclude returns,"* *"you used PostedDate,"* *"BETWEEN includes the end points,"* *"COUNT(\*) vs COUNT(Company)."*

There are 530 such diagnosed mistakes, each calculated by running the wrong method on the real data. This matters because the exam is oral. An examiner asks *why* a number is what it is, and a student who has seen "your answer is wrong because Excel read the dates as day/month" can explain the ETL problem, which is a learning objective of the course. A student who has only seen "wrong" cannot. It also serves the original site's own goal: knowing *"I would have got this right"* lowers exam anxiety in a way that *"the chatbot thinks my approach sounds reasonable"* cannot. And it is consistent with the original site, which already shows answers for the interpretation exams but gives none for the larger manipulation part.

## Why the starting materials make this case harder than earlier cases

Earlier cases started from one clean input and one clear question. Here the materials are 11 datasets in 7 formats: pipe-delimited CSV, a comma-separated `.txt` with US dates, `.xlsx`, a macro `.xlsm` whose three sheets must be merged, and SQLite databases. They come with long Word case descriptions, and most of the cases have **no answer key**: only the NYC permits and the Chinook questions came with answers. So before building anything, every answer had to be computed and checked against the few keys that exist. The data also contains deliberate traps that change the answer: US dates that a Danish Excel misreads, job codes with optional department letters, a PreparerID that is only unique together with BusinessUnitID, and returns stored as negative amounts. Two databases were too large to upload to GitHub, so smaller practice subsets had to be designed and all their answers recomputed. Finally, many case tasks are open-ended (memos, "ask the right questions", the four V's), so the hard part was deciding which skills can be turned into questions with one checkable answer. Generating code was the easy part.
