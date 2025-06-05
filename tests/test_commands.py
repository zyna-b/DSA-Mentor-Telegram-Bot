import gspread

# Authenticate and open the sheet
gc = gspread.service_account(filename='google-cloud-service-creds-for-sheets.json')
sh = gc.open('Copy of DSA by Shradha Ma\'am')  # Use exact sheet name
worksheet = sh.worksheet('DSA in 2.5 Months')  # Use exact tab name

# Fetch all records (skip empty rows)
records = [row for row in worksheet.get_all_records() if row['Question (375)']]

# Example user preferences (replace with actual user input in your bot)
user_preferences = {
    "difficulties": ["Easy", "Medium"],
    "topics": ["Arrays", "Strings"],
    "company": "Google"
}

def filter_questions(records, preferences):
    result = []
    for row in records:
        # Check difficulty
        if row['Difficulty'] not in preferences['difficulties']:
            continue
        # Check topic
        if row['Topics'] not in preferences['topics']:
            continue
        # Check company (case-insensitive substring match)
        companies = row['Companies'].lower() if row['Companies'] else ""
        if preferences['company'].lower() not in companies:
            continue
        result.append(row)
    return result

matching_questions = filter_questions(records, user_preferences)

# Print first matching question as sample
if matching_questions:
    print("Here's a matching question for you:")
    first = matching_questions[0]
    print(f"Topic: {first['Topics']}")
    print(f"Question: {first['Question (375)']}")
    print(f"Companies: {first['Companies']}")
    print(f"Difficulty: {first['Difficulty']}")
else:
    print("No matching questions found.")
