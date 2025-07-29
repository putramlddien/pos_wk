input_file = 'pos_wk.sql'
output_file = 'pos_wk2.sql'

with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
    for line in infile:
        # Hapus perintah khusus SQLite
        if line.startswith("PRAGMA") or line.startswith("BEGIN TRANSACTION") or line.startswith("COMMIT"):
            continue
        if "sqlite_sequence" in line or "WITHOUT ROWID" in line:
            continue

        # Konversi tipe data
        line = line.replace("AUTOINCREMENT", "AUTO_INCREMENT")
        line = line.replace("INTEGER PRIMARY KEY", "INT PRIMARY KEY AUTO_INCREMENT")

        # Ganti tanda kutip
        line = line.replace('"', '`')

        # Optional: Ganti tipe text
        line = line.replace("TEXT", "VARCHAR(255)")

        outfile.write(line)
