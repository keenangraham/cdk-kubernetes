FROM apache/spark:4.1.2

USER root
RUN mkdir -p /tmp/jars && \
    cd /tmp/jars && \
    curl -O https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.5.0/hadoop-aws-3.5.0.jar && \
    curl -O https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.797/aws-java-sdk-bundle-1.12.797.jar && \
    mv *.jar $SPARK_HOME/jars/ && \
    cd / && \
    rm -rf /tmp/jars && \
    pip3 install boto3
USER spark
