FROM maven:3.9.9-eclipse-temurin-11 AS build
WORKDIR /build
COPY pom.xml .
RUN mvn -B -q dependency:go-offline
COPY src ./src
RUN mvn -B -q package -DskipTests

FROM flink:1.20.2
COPY --from=build /build/target/agent-metrics-flink-job-1.0.0.jar /opt/flink/usrlib/agent-metrics-flink-job.jar
