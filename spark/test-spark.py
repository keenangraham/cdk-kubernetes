from pyspark.sql import SparkSession
from pyspark.sql import Row
from pyspark.sql.functions import col, regexp_extract


def main():
    spark = SparkSession.builder \
        .appName("S3 Log Reader") \
        .getOrCreate()

    data = [
        Row(name="feKlalice", age=30),
        Row(name="Bob", age=25),
        Row(name="Charlie", age=35),
        Row(name="David", age=40)
    ]

    df = spark.createDataFrame(data)

    df.show()

    row_count = df.count()

    print(f"Number of rows in the DataFrame: {row_count}")
#    df = spark.read.text("s3a://encode-imputation-logs/")
    df = spark.read.text("s3a://igvf-files-dev-logs/")
#    df.persist()
    print('Number of logs', df.count())


if __name__ == "__main__":
    main()
