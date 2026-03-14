package com.example.oilrisk_alert.mapper;

import com.example.oilrisk_alert.entity.RiskFactor;
import org.apache.ibatis.annotations.Mapper;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@Mapper
public interface FactorMapper {

    LocalDate findLatestDate();

    List<RiskFactor> findByDate(LocalDate date);

    List<RiskFactor> findTopByDateOrderByAbsShap(LocalDate date, int limit);

    List<Map<String, Object>> findWeightHistory(LocalDate start, LocalDate end);
}
