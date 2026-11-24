# Predictions

Expected answers, written before the code. Never edited afterwards.

## Step 0
Newsletter: Kettlebird Tea's Steep Club, for people who like loose-leaf tea.

## Step 1: counts
24 subscribers in total, 8 in each of green, black and oolong. 20 gave consent.

## Step 2: dates (run date 2026-11-20)
"The last 30 days" is 2026-10-21 to 2026-11-20, both ends included, so 21 October counts.
7 joined in that window. 8 joined on or after 2026-10-01.
Next send: 2026-12-07. The one after: 2027-01-04.

## Step 3: 2026-02-30
It crashes with ValueError from date.fromisoformat, raised inside load_subscribers. After the fix it names the row.

## Step 5: subject cases
- "The Steep Club opens Monday": no problems
- "Your Steep Club box ships on Monday with new teas." (50): no problems
- "Your Steep Club box ships on Monday with fresh teas" (51): too long
- "": empty
- "   ": empty
- no Subject line: missing

## Step 11: new sign-ups
3 good (Zoe, Fern, Gus) and 5 bad: rows 3 email, 4 group, 5 date, 6 name, 7 consent.

## Step 16 to 18: sending
Sending issue-01 twice leaves 20 emails on the practice server, not 40.
A 422 is shown and never retried. A 503 then 200 succeeds on try 2.

## Step 25: guard
sara.ali@gmail.com exits 2 with a reason. delivered@resend.dev exits 0. Another tool exits 0.
