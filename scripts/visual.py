import os
import pandas as pd
import matplotlib.pyplot as plt
import paths

# Load raw and cleaned
raw_mon = pd.read_csv(os.path.join(paths.RAW_CSV, "Monday-WorkingHours.pcap_ISCX.csv"))
raw_tue = pd.read_csv(os.path.join(paths.RAW_CSV, "Tuesday-WorkingHours.pcap_ISCX.csv"))
raw_wed = pd.read_csv(os.path.join(paths.RAW_CSV, "Wednesday-workingHours.pcap_ISCX.csv"))

raw_df = pd.concat([raw_mon, raw_tue, raw_wed], ignore_index=True)

clean_df = pd.read_csv(os.path.join(paths.PROCESSED, "clean_train.csv"))

# Row counts
labels = ["Raw Data", "Cleaned Data"]
values = [len(raw_df), len(clean_df)]

plt.bar(labels, values, color=['#293961', '#293961'])
plt.title("Row Count Before vs After Cleaning")
plt.ylabel("Number of Rows")
plt.show()

print("Raw rows:", len(raw_df))
print("Cleaned rows:", len(clean_df))


raw_missing = raw_df.isnull().sum().sum()
clean_missing = clean_df.isnull().sum().sum()

labels = ["Raw", "Cleaned"]
values = [raw_missing, clean_missing]

plt.bar(labels, values, color=['#293961', '#293961'])
plt.title("Missing Values Before vs After Cleaning")
plt.ylabel("Number of Values")
plt.show()

print("Raw missing:", raw_missing)
print("Clean missing:", clean_missing)


raw_dup = raw_df.duplicated().sum()
clean_dup = clean_df.duplicated().sum()

labels = ["Raw", "Cleaned"]
values = [raw_dup, clean_dup]

plt.bar(labels, values, color=['#293961', '#293961'])
plt.title("Duplicate Rows Before vs After Cleaning")
plt.ylabel("Number of Duplicate Rows")
plt.show()

print("Raw duplicates:", raw_dup)
print("Clean duplicates:", clean_dup)


retained = (len(clean_df) / len(raw_df)) * 100

print(f"Data retained after cleaning: {retained:.2f}%")