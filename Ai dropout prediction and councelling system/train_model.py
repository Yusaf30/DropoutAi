import random
import pickle
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.metrics import classification_report, confusion_matrix

# 1. Create a sample dataset manually using pandas.
# We will make 80 rows of student records with attendance, avg_marks, study_hours, backlogs.
rows = []
for i in range(80):
    attendance = random.randint(30, 100)
    avg_marks = random.randint(30, 100)
    study_hours = random.randint(1, 8)
    backlogs = random.randint(0, 4)

    # 3. Define dropout logic based on the project requirement.
    if attendance < 50 or backlogs > 2:
        dropout = 1
    else:
        dropout = 0

    rows.append({
        'attendance': attendance,
        'avg_marks': avg_marks,
        'study_hours': study_hours,
        'backlogs': backlogs,
        'dropout': dropout
    })

# Convert the list of records into a DataFrame.
df = pd.DataFrame(rows)
print('Sample data:')
print(df.head())
print('\nDataset size:', len(df))

# 5. Split data into train and test sets.
# We use 80% of the data for training and 20% for testing.
X = df[['attendance', 'avg_marks', 'study_hours', 'backlogs']]
y = df['dropout']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 4. Train a RandomForestClassifier model.
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 6. Print accuracy on the test set.
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f'Accuracy: {accuracy:.2f}')
# 🔥 Classification Report
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# 🔥 Confusion Matrix
print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# 7. Save the trained model as "model.pkl" using pickle.
with open('model.pkl', 'wb') as file:
    pickle.dump(model, file)

print('Trained model saved to model.pkl')
