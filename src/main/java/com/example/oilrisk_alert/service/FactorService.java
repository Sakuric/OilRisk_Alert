package com.example.oilrisk_alert.service;

import com.example.oilrisk_alert.dto.WeightDTO;
import com.example.oilrisk_alert.vo.FactorVO;
import com.example.oilrisk_alert.vo.RadarScoreVO;
import com.example.oilrisk_alert.vo.WeightUpdateResultVO;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

public interface FactorService {

    List<RadarScoreVO> getRadarScores(LocalDate date);

    List<FactorVO> getExplain(LocalDate date);

    WeightUpdateResultVO updateWeights(WeightDTO dto);

    List<Map<String, Object>> getWeightHistory(int months);
}
