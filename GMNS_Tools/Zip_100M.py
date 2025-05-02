import os
import zipfile

def find_and_compress_large_files(base_dir='.', size_threshold_mb=100, compress=False):
    size_threshold_bytes = size_threshold_mb * 1024 * 1024
    ignore_dirs = {'.git', '__pycache__', '.idea', '.vscode', 'node_modules', '.DS_Store'}

    for root, dirs, files in os.walk(base_dir):
        # Filter out unwanted directories in-place
        dirs[:] = [d for d in dirs if d not in ignore_dirs]

        for file in files:
            file_path = os.path.join(root, file)
            try:
                file_size = os.path.getsize(file_path)
                if file_size >= size_threshold_bytes:
                    print(f"Found large file: {file_path} ({file_size / 1024 / 1024:.2f} MB)")

                    if compress:
                        zip_path = f"{file_path}.zip"
                        print(f"Compressing to: {zip_path}")
                        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            zipf.write(file_path, arcname=file)
                        os.remove(file_path)
                        print(f"Deleted original file: {file_path}")

            except Exception as e:
                print(f"Error processing {file_path}: {e}")

# === USAGE ===
# Set compress=True to enable compression and deletion
find_and_compress_large_files(base_dir='..', size_threshold_mb=100, compress=False)
