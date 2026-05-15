import pandas as pd
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report


# Load dataset
df = pd.read_csv("training/data/tickets.csv")

# Features and labels
X = df["text"]
y = df["priority"]

# Vectorization
vectorizer = TfidfVectorizer()

X_vectorized = vectorizer.fit_transform(X)

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X_vectorized,
    y,
    test_size=0.2,
    random_state=42
)

# Model
model = LogisticRegression()

# Train
model.fit(X_train, y_train)

# Predictions
predictions = model.predict(X_test)

# Metrics
print(classification_report(y_test, predictions))

# Save artifacts
joblib.dump(model, "training/models/model.pkl")
joblib.dump(vectorizer, "training/models/vectorizer.pkl")

print("Model and vectorizer saved successfully.")