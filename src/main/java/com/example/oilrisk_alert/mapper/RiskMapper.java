package com.example.oilrisk_alert.mapper;

import com.example.oilrisk_alert.entity.RiskIndex;
import org.apache.ibatis.annotations.Mapper;

import java.time.LocalDate;
import java.util.List;

@Mapper
public interface RiskMapper {

    RiskIndex findLatest();

    List<RiskIndex> findByDateRange(LocalDate start, LocalDate end);
}
