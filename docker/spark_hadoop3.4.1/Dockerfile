#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
FROM eclipse-temurin:11-jre-focal

ARG spark_uid=185

RUN groupadd --system --gid=${spark_uid} spark && \
    useradd --system --uid=${spark_uid} --gid=spark spark

RUN set -ex; \
    apt-get update; \
    apt-get install -y gnupg2 wget bash tini libc6 libpam-modules krb5-user libnss3 procps net-tools gosu libnss-wrapper; \
    apt-get install -y python3 python3-pip; \
    mkdir -p /opt/spark; \
    mkdir -p /opt/hadoop; \
    mkdir /opt/spark/python; \
    mkdir -p /opt/spark/examples; \
    mkdir -p /opt/spark/work-dir; \
    chmod g+w /opt/spark/work-dir; \
    touch /opt/spark/RELEASE; \
    chown -R spark:spark /opt/spark; \
    chown -R spark:spark /opt/hadoop; \
    echo "auth required pam_wheel.so use_uid" >> /etc/pam.d/su; \
    rm -rf /var/lib/apt/lists/*

# Install Apache Spark
# https://downloads.apache.org/spark/KEYS
ENV SPARK_TGZ_URL=https://archive.apache.org/dist/spark/spark-3.5.5/spark-3.5.5-bin-without-hadoop.tgz
ENV HADOOP_TGZ_URL=https://dlcdn.apache.org/hadoop/common/hadoop-3.4.1/hadoop-3.4.1.tar.gz

RUN set -ex; \
    export SPARK_TMP="$(mktemp -d)"; \
    cd $SPARK_TMP; \
    wget -nv -O spark.tgz "$SPARK_TGZ_URL"; \
    tar -xf spark.tgz --strip-components=1; \
    chown -R spark:spark .; \
    mv jars /opt/spark/; \
    mv RELEASE /opt/spark/; \
    mv bin /opt/spark/; \
    mv sbin /opt/spark/; \
    mv kubernetes/dockerfiles/spark/decom.sh /opt/; \
    mv examples /opt/spark/; \
    ln -s "$(basename /opt/spark/examples/jars/spark-examples_*.jar)" /opt/spark/examples/jars/spark-examples.jar; \
    mv kubernetes/tests /opt/spark/; \
    mv data /opt/spark/; \
    mv python/pyspark /opt/spark/python/pyspark/; \
    mv python/lib /opt/spark/python/lib/; \
    mv R /opt/spark/; \
    chmod a+x /opt/decom.sh; \
    cd ..; \
    rm -rf "$SPARK_TMP";

RUN set -ex; \
    export HADOOP_TMP="$(mktemp -d)"; \
    cd $HADOOP_TMP; \
    wget -nv -O hadoop.tgz "$HADOOP_TGZ_URL"; \
    tar -xf hadoop.tgz --strip-components=1; \
    chown -R spark:spark .; \
    mv bin /opt/hadoop/; \
    mv etc /opt/hadoop/; \
    mv include /opt/hadoop/; \
    mv lib /opt/hadoop/; \
    mv libexec /opt/hadoop/; \
    mv sbin /opt/hadoop/; \
    mv share /opt/hadoop/; \
    mv licenses-binary /opt/hadoop/; \
    mv LICENSE* /opt/hadoop/; \
    mv NOTICE* /opt/hadoop/; \
    mv README* /opt/hadoop/; \
    cd ..; \
    rm -rf "$HADOOP_TMP";

COPY entrypoint.sh /opt/

ENV SPARK_HOME=/opt/spark
ENV HADOOP_HOME=/opt/hadoop

WORKDIR /opt/spark/work-dir

USER spark

RUN mkdir -p /tmp/jars && \
    cd /tmp/jars && \
    curl -O https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.4.1/hadoop-aws-3.4.1.jar && \
    curl -O https://repo1.maven.org/maven2/software/amazon/awssdk/bundle/2.24.6/bundle-2.24.6.jar && \
    curl -O https://repo1.maven.org/maven2/org/wildfly/openssl/wildfly-openssl/1.1.3.Final/wildfly-openssl-1.1.3.Final.jar && \
    mv *.jar $SPARK_HOME/jars/ && \
    rm -rf /tmp/jars

ENTRYPOINT [ "/opt/entrypoint.sh" ]
