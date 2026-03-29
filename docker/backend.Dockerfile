FROM docker.m.daocloud.io/library/maven:3.9.9-eclipse-temurin-17 AS build

WORKDIR /build

COPY pom.xml ./
COPY src ./src

RUN mvn -q -DskipTests package

FROM docker.m.daocloud.io/library/eclipse-temurin:17-jre

WORKDIR /app

COPY --from=build /build/target/OilRisk_Alert-0.0.1-SNAPSHOT.jar ./app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "/app/app.jar"]
