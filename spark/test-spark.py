from pyspark.sql import SparkSession
from pyspark.sql import Row
from pyspark.sql.functions import col, regexp_extract



def main():
    spark = SparkSession.builder \
    .appName("S3 Log Reader") \
    .config("spark.hadoop.mapreduce.input.fileinputformat.split.minsize", "134217728")  \
    .config("spark.hadoop.mapreduce.input.fileinputformat.split.maxsize", "268435456")  \
    .getOrCreate()

    log_regex_pattern = r'([^ ]*) ([^ ]*) \[(.*?)\] ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ("[^"]+"|-) (\d+|-|-) ([^ ]*) (\d+|-|-) (\d+|-|-) (\d+|-|-) (\d+|-|-) ("[^"]*"|-) ("[^"]*"|-) ([^ ]*)'
    files_to_read = [
        "s3a://encode-public-logs/2021-02-07-00-12-01-357181973ED3DF46",
        "s3a://encode-public-logs/2021-02-07-00-12-11-753BD5A9E4695EC8",
        "s3a://encode-public-logs/2021-02-07-00-12-12-A6B937F768674999",
        "s3a://encode-public-logs/2021-02-07-00-12-16-69EB0FEF8A14F015",
        "s3a://encode-public-logs/2021-02-07-00-12-18-D8A268D6E5130527",
        "s3a://encode-public-logs/2021-02-07-00-12-19-77B9F97912098605",
        "s3a://encode-public-logs/2021-02-07-00-12-20-5441F5DA895F74A2",
        "s3a://encode-public-logs/2021-02-07-00-12-21-0BC83255EA1C70AE",
        "s3a://encode-public-logs/2021-02-07-00-12-21-C896992746908423",
        "s3a://encode-public-logs/2021-02-07-00-12-23-2DFE09AE9599A987",
        "s3a://encode-public-logs/2021-02-07-00-12-23-3E65469D4FCDEBCE",
        "s3a://encode-public-logs/2021-02-07-00-12-30-8FAB373CC98199F8",
        "s3a://encode-public-logs/2021-02-07-00-12-34-460DA073A28F5D9F",
        "s3a://encode-public-logs/2021-02-07-00-12-34-49B5A221EBFDD2CE",
        "s3a://encode-public-logs/2021-02-07-00-12-34-9C4473821D19B611",
        "s3a://encode-public-logs/2021-02-07-00-12-35-0F987F8D6869C814",
        "s3a://encode-public-logs/2021-02-07-00-12-35-2DC3CB5976381E53",
        "s3a://encode-public-logs/2021-02-07-00-12-37-80C538A38E4E4B8A",
        "s3a://encode-public-logs/2021-02-07-00-12-38-82E59C5A596A6D83",
        "s3a://encode-public-logs/2021-02-07-00-12-38-9038176B5E218718",
        "s3a://encode-public-logs/2021-02-07-00-12-38-A8EC7D0F925EAFBC",
        "s3a://encode-public-logs/2021-02-07-00-12-39-01299C332CCDC5C2",
        "s3a://encode-public-logs/2021-02-07-00-12-40-A5B3DF3499282392",
        "s3a://encode-public-logs/2021-02-07-00-12-41-4F56CAB932A62A9D",
        "s3a://encode-public-logs/2021-02-07-00-12-41-8463BF1D5FE6C340",
        "s3a://encode-public-logs/2021-02-07-00-12-41-D965D844417C8BB1",
        "s3a://encode-public-logs/2021-02-07-00-12-43-7B93D8901013DB25",
        "s3a://encode-public-logs/2021-02-07-00-12-47-1186F308B5441CF6",
        "s3a://encode-public-logs/2021-02-07-00-12-48-8D2AB502E99B1D26",
        "s3a://encode-public-logs/2021-02-07-00-12-51-A90C132401E3DDC1",
        "s3a://encode-public-logs/2021-02-07-00-12-52-8164A7CFD537DEAC",
        "s3a://encode-public-logs/2021-02-07-00-12-52-87B68ADC35A50B24",
        "s3a://encode-public-logs/2021-02-07-00-12-52-A4C75D2E17C4F422",
        "s3a://encode-public-logs/2021-02-07-00-12-52-FF0D5A9CC7DEF071",
        "s3a://encode-public-logs/2021-02-07-00-12-53-746D063CBF247B61",
        "s3a://encode-public-logs/2021-02-07-00-12-54-29E8E2D86591C1B0",
        "s3a://encode-public-logs/2021-02-07-00-12-55-14F5A6F7B440413E",
        "s3a://encode-public-logs/2021-02-07-00-12-55-B25C6CDD649D6057",
        "s3a://encode-public-logs/2021-02-07-00-12-56-4D4266EB6D01BE40",
        "s3a://encode-public-logs/2021-02-07-00-12-56-A995337981558AED",
        "s3a://encode-public-logs/2021-02-07-00-12-57-1E3EEBB289E442AC",
        "s3a://encode-public-logs/2021-02-07-00-12-57-3681F97FD1B7B3A0",
        "s3a://encode-public-logs/2021-02-07-00-12-57-6A50CD672272928E",
        "s3a://encode-public-logs/2021-02-07-00-12-58-2A3C07388FF88AD0",
        "s3a://encode-public-logs/2021-02-07-00-12-58-845B8AD2798E51EC",
        "s3a://encode-public-logs/2021-02-07-00-12-59-36C702B6202FB5E5",
    ]
    df = spark.read.text(files_to_read)
    print('Number of logs', df.count())

    parsed_df = df.select(
    'value',
    regexp_extract(col('value'), log_regex_pattern, 1).alias('bucket_owner'),
    regexp_extract(col('value'), log_regex_pattern, 2).alias('bucket_name'),
    regexp_extract(col('value'), log_regex_pattern, 3).alias('timestamp'),
    regexp_extract(col('value'), log_regex_pattern, 4).alias('remote_ip'),
    regexp_extract(col('value'), log_regex_pattern, 5).alias('requester'),
    regexp_extract(col('value'), log_regex_pattern, 6).alias('request_id'),
    regexp_extract(col('value'), log_regex_pattern, 7).alias('operation'),
    regexp_extract(col('value'), log_regex_pattern, 8).alias('key'),
    regexp_extract(col('value'), log_regex_pattern, 9).alias('request_uri'),
    regexp_extract(col('value'), log_regex_pattern, 10).alias('http_status'),
    regexp_extract(col('value'), log_regex_pattern, 11).alias('error_code'),
    regexp_extract(col('value'), log_regex_pattern, 12).alias('bytes_sent'),
    regexp_extract(col('value'), log_regex_pattern, 13).alias('object_size'),
    regexp_extract(col('value'), log_regex_pattern, 14).alias('total_time'),
    regexp_extract(col('value'), log_regex_pattern, 15).alias('turn_around_time'),
    regexp_extract(col('value'), log_regex_pattern, 16).alias('referrer'),
    regexp_extract(col('value'), log_regex_pattern, 17).alias('user_agent'),
    regexp_extract(col('value'), log_regex_pattern, 18).alias('version_id')
    )

    parsed_df.write.mode('overwrite').parquet('s3a://spark-log-parsing-test/encode-logs')


if __name__ == "__main__":
    main()
