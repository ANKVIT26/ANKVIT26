# -*- coding: utf-8 -*-
"""CarTracking.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1LcZU0hvZxWSfUOuDKOy1xZb3P1-3SJrk
"""

# Step 1: Install necessary libraries
!pip install opencv-python pytesseract matplotlib scikit-learn folium easyocr torch torchvision
!apt-get install tesseract-ocr libtesseract-dev

# Step 2: Import libraries
import cv2
import numpy as np
import sqlite3
import time
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix
import re
import os
import easyocr  # For OCR functionality
import folium  # For mapping
from google.colab.patches import cv2_imshow  # For displaying images in Colab

# Step 3: Create or connect to a database for logging detected plates
conn = sqlite3.connect('vehicle_tracking.db', uri=True)
c = conn.cursor()

# Create a table for storing vehicle logs if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS vehicle_logs
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              plate TEXT,
              timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

# Function to log detected plate into the database
def log_plate(plate):
    c.execute("INSERT INTO vehicle_logs (plate) VALUES (?)", (plate,))
    conn.commit()

def clean_plate_text(text):
    """Clean the detected text from EasyOCR."""
    return re.sub(r'[^A-Za-z0-9]', '', text)

def save_detected_plate_image(plate_image, plate_number, frame_count):
    """Save the detected plate image to a file."""
    if not os.path.exists('detected_plates'):
        os.makedirs('detected_plates')

    filename = f'detected_plates/{plate_number}_{frame_count}.png'
    cv2.imwrite(filename, plate_image)

# Step 4: Function to detect number plates in a video frame using EasyOCR
def detect_number_plate(frame, frame_count): # Add frame_count as an argument
    reader = easyocr.Reader(['en'])  # Initialize EasyOCR reader for English language

    # Convert frame to RGB since OpenCV uses BGR by default
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Use EasyOCR to detect text in the frame
    results = reader.readtext(rgb_frame)

    detected_plates = []

    for (bbox, text, prob) in results:
        # Filter results based on confidence threshold (e.g., 0.5)
        if prob > 0.5:
            detected_plate = clean_plate_text(text)
            detected_plates.append(detected_plate)
            # Draw bounding box around detected plates
            (top_left, top_right, bottom_right, bottom_left) = bbox
            top_left = tuple(map(int, top_left))
            bottom_right = tuple(map(int, bottom_right))
            cv2.rectangle(frame, top_left, bottom_right, (255, 0, 0), 2)
            log_plate(detected_plate)  # Log the detected plate into the database

            # Save the detected plate image
            plate_image = frame[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]
            save_detected_plate_image(plate_image, detected_plate, frame_count)

    return frame, detected_plates

# Step 5: Process the video file and detect number plates every 5th frame
def process_video(video_path):
    cap = cv2.VideoCapture(video_path)
    all_detected_plates = []

    if not cap.isOpened():
        print("Error: Could not open video.")
        return all_detected_plates

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))  # Get total number of frames in the video.
    print(f"Total frames in video: {total_frames}")

    frame_count = 0  # Initialize frame count

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1  # Increment frame count

        # Process only every 5th frame
        if frame_count % 5 == 0:
            processed_frame, detected_plates = detect_number_plate(frame, frame_count) # Pass frame_count as argument

            if detected_plates:
                all_detected_plates.extend(detected_plates)  # Collect all detected plates

            # Display the processed frame using cv2_imshow instead of cv2.imshow
            cv2_imshow(processed_frame)

    cap.release()

    return all_detected_plates
# Step 6: Run the video processing function on your video file path
detected_plates = process_video('/content/CarTrack.mp4')

# Assuming you have actual labels for comparison (for demonstration purposes)
actual_labels = ['HR140777'] * len(detected_plates)

# Generate confusion matrix (assuming both lists are of same length)
cm = confusion_matrix(actual_labels[:len(detected_plates)], detected_plates)

# Plotting the confusion matrix
plt.figure(figsize=(8,6))
plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
plt.title('Confusion Matrix')
plt.colorbar()
tick_marks = np.arange(len(set(actual_labels)))
plt.xticks(tick_marks, set(actual_labels), rotation=45)
plt.yticks(tick_marks, set(actual_labels))

thresh = cm.max() / 2.
for i, j in np.ndindex(cm.shape):
    plt.text(j, i, format(cm[i, j], 'd'),
             horizontalalignment="center",
             color="white" if cm[i, j] > thresh else "black")

plt.ylabel('True label')
plt.xlabel('Predicted label')
plt.tight_layout()
plt.show()

# Step 7: Create a map depicting the route from A to G
def create_route_map():
    locations = {
        'A': (28.7041, 77.1025),
        'B': (28.7045, 77.1030),
        'C': (28.7050, 77.1040),
        'D': (28.7060, 77.1050),
        'E': (28.7070, 77.1060),
        'F': (28.7080, 77.1070),
        'G': (28.7090, 77.1080)
    }

    m = folium.Map(location=locations['A'], zoom_start=14)

    for loc in locations:
        folium.Marker(location=locations[loc], popup=loc).add_to(m)

    folium.PolyLine(locations.values(), color='blue', weight=2.5).add_to(m)

    m.save('route_map.html')

create_route_map()

# Query logs (for demonstration)
print("Logged Plates:")
for row in c.execute('SELECT * FROM vehicle_logs ORDER BY timestamp'):
    print(row)

# Close the database connection when done
conn.close()