package com.example.oilrisk_alert.service;

import com.example.oilrisk_alert.vo.ModelSignalVO;
import com.example.oilrisk_alert.vo.RiskCurrentVO;
import com.example.oilrisk_alert.vo.TimeseriesVO;

import java.time.LocalDate;
import java.util.Map;

public interface RiskService {

    RiskCurrentVO getCurrentRisk();

    TimeseriesVO getTimeseries(LocalDate start, LocalDate end);

    Map<String, Object> getPredictionFromEngine();

    ModelSignalVO getModelSignals();
}
