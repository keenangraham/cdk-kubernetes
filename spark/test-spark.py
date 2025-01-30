from pyspark.sql import SparkSession
from pyspark.sql import Row


def main():
    spark = SparkSession.builder \
        .appName("TestSpark") \
        .getOrCreate()


    data = [
        Row(name="Alice", age=30),
        Row(name="Bob", age=25),
        Row(name="Charlie", age=35),
        Row(name="David", age=40)
    ]

    df = spark.createDataFrame(data)

    df.show()

    row_count = df.count()

    print(f"Number of rows in the DataFrame: {row_count}")

    spark.stop()

if __name__ == "__main__":
    main()
