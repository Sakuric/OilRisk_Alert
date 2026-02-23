package com.example.oilrisk_alert.mapper;

import com.example.oilrisk_alert.entity.RiskFactor;
import org.apache.ibatis.annotations.Mapper;

import java.time.LocalDate;
import java.util.List;

@Mapper
public interface FactorMapper {

    LocalDate findLatestDate();

    List<RiskFactor> findByDate(LocalDate date);

    List<RiskFactor> findTopByDateOrderByAbsShap(LocalDate date, int limit);
}
