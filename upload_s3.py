import os
import boto3
from botocore.exceptions import ClientError

BUCKET = "bb-audio-test1"

def main():
    filename = input("Enter audio file name: ").strip()

    if not filename:
        print("No file name provided.")
        return

    # Expand ~ and convert to absolute path
    file_path = os.path.abspath(os.path.expanduser(filename))

    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return

    file_name = os.path.basename(file_path)

    print(f"\nUploading:")
    print(f"  Local file : {file_path}")
    print(f"  S3 bucket  : s3://{BUCKET}/{file_name}")

    s3 = boto3.client("s3")

    try:
        s3.upload_file(
            file_path,
            BUCKET,
            file_name
        )

        print("\nUpload successful!")
        print(f"s3://{BUCKET}/{file_name}")

    except ClientError as e:
        print("\nUpload failed:")
        print(e)


if __name__ == "__main__":
    main()
