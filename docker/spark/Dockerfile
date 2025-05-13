FROM spark:3.5.3


RUN mkdir -p /tmp/jars && \
    cd /tmp/jars && \
    curl -O https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar && \
    curl -O https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.11.1026/aws-java-sdk-bundle-1.11.1026.jar && \
    mv *.jar $SPARK_HOME/jars/ && \
    rm -rf /tmp/jars
USER root
RUN pip3 install boto3
USER spark