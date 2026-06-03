FROM apache/spark:4.1.2

USER root
RUN mkdir -p /tmp/jars && \
    cd /tmp/jars && \
    curl -O https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.4.2/hadoop-aws-3.4.2.jar && \
    curl -O https://repo1.maven.org/maven2/software/amazon/awssdk/bundle/2.29.52/bundle-2.29.52.jar && \
    mv *.jar $SPARK_HOME/jars/ && \
    cd / && \
    rm -rf /tmp/jars && \
    pip3 install boto3
USER spark
