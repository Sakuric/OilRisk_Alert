package com.example.oilrisk_alert.service.impl;

import com.example.oilrisk_alert.common.BusinessException;
import com.example.oilrisk_alert.entity.Alert;
import com.example.oilrisk_alert.entity.RiskFactor;
import com.example.oilrisk_alert.entity.RiskIndex;
import com.example.oilrisk_alert.mapper.AlertMapper;
import com.example.oilrisk_alert.mapper.FactorMapper;
import com.example.oilrisk_alert.mapper.RiskMapper;
import com.example.oilrisk_alert.service.RiskService;
import com.example.oilrisk_alert.util.LttbUtil;
import com.example.oilrisk_alert.vo.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class RiskServiceImpl implements RiskService {

    private final RiskMapper riskMapper;
    private final FactorMapper factorMapper;
    private final AlertMapper alertMapper;
    private final RestTemplate restTemplate;

    @Value("${python.engine.url}")
    private String pythonEngineUrl;

    private static final int LTTB_THRESHOLD = 2000;

    @Override
    public RiskCurrentVO getCurrentRisk() {
        RiskIndex latest = riskMapper.findLatest();
        if (latest == null) {
            throw new BusinessException(404, "No risk data available");
        }

        List<RiskFactor> topFactors = factorMapper.findTopByDateOrderByAbsShap(latest.getDate(), 5);

        RiskCurrentVO vo = new RiskCurrentVO();
        vo.setRiskIndex(latest.getRiskIndex());
        vo.setRiskLevel(latest.getRiskLevel());
        vo.setDate(latest.getDate().toString());

        List<FactorVO> factorVOs = new ArrayList<>();
        for (RiskFactor rf : topFactors) {
            FactorVO fv = new FactorVO();
            fv.setName(rf.getFactorName());
            fv.setNameZh(rf.getFactorNameZh());
            fv.setShap(rf.getShapValue());
            fv.setCategory(rf.getCategory());
            fv.setValue(rf.getValue());
            factorVOs.add(fv);
        }
        vo.setTopFactors(factorVOs);

        // 填充实时因子采集扩展字段
        try {
            String statusUrl = pythonEngineUrl + "/collect/status";
            ResponseEntity<Map<String, Object>> statusResp = restTemplate.exchange(
                    statusUrl, HttpMethod.GET, null,
                    new ParameterizedTypeReference<>() {}
            );
            Map<String, Object> statusBody = statusResp.getBody();
            if (statusBody != null) {
                Object dataDate = statusBody.get("data_date");
                Object predTime = statusBody.get("last_prediction_time");
                vo.setDataDate(dataDate != null ? String.valueOf(dataDate) : "");
                vo.setUpdatedAt(predTime != null ? String.valueOf(predTime) : "");
                String collStatus = statusBody.get("last_collection_status") != null
                        ? String.valueOf(statusBody.get("last_collection_status")) : "";
                boolean isRealtime = "SUCCESS".equals(collStatus) || "PARTIAL".equals(collStatus);
                vo.setDataSource(isRealtime ? "realtime" : "historical");
            }
        } catch (RestClientException e) {
            log.debug("Could not fetch collect status for RiskCurrentVO: {}", e.getMessage());
            vo.setDataSource("historical");
        }

        return vo;
    }

    @Override
    public TimeseriesVO getTimeseries(LocalDate start, LocalDate end) {
        // BR-02: default to last 2 years
        if (end == null) {
            end = LocalDate.now();
        }
        if (start == null) {
            start = end.minusYears(2);
        }

        List<RiskIndex> riskData = riskMapper.findByDateRange(start, end);
        List<Alert> alertData = alertMapper.findByDateRange(start, end);

        // Prepare raw data arrays
        List<String> dates = new ArrayList<>(riskData.size());
        List<BigDecimal> oilPrices = new ArrayList<>(riskData.size());
        List<BigDecimal> riskIndices = new ArrayList<>(riskData.size());

        for (RiskIndex ri : riskData) {
            dates.add(ri.getDate().toString());
            oilPrices.add(ri.getOilPrice());
            riskIndices.add(ri.getRiskIndex());
        }

        // LTTB downsampling if >2000 points
        if (riskData.size() > LTTB_THRESHOLD) {
            // Build [index, value] pairs for LTTB
            List<double[]> oilPriceData = new ArrayList<>(riskData.size());
            List<double[]> riskIndexData = new ArrayList<>(riskData.size());
            for (int i = 0; i < riskData.size(); i++) {
                oilPriceData.add(new double[]{i, oilPrices.get(i).doubleValue()});
                riskIndexData.add(new double[]{i, riskIndices.get(i).doubleValue()});
            }

            List<double[]> sampledOil = LttbUtil.downsample(oilPriceData, LTTB_THRESHOLD);
            List<double[]> sampledRisk = LttbUtil.downsample(riskIndexData, LTTB_THRESHOLD);

            // Collect all unique indices from both downsampled sets
            java.util.Set<Integer> indexSet = new java.util.TreeSet<>();
            for (double[] p : sampledOil) indexSet.add((int) p[0]);
            for (double[] p : sampledRisk) indexSet.add((int) p[0]);

            List<String> newDates = new ArrayList<>();
            List<BigDecimal> newOilPrices = new ArrayList<>();
            List<BigDecimal> newRiskIndices = new ArrayList<>();
            for (int idx : indexSet) {
                newDates.add(dates.get(idx));
                newOilPrices.add(oilPrices.get(idx));
                newRiskIndices.add(riskIndices.get(idx));
            }
            dates = newDates;
            oilPrices = newOilPrices;
            riskIndices = newRiskIndices;
        }

        // Build alert markers
        List<AlertTimeseriesVO> alertVOs = new ArrayList<>();
        for (Alert alert : alertData) {
            AlertTimeseriesVO avo = new AlertTimeseriesVO();
            avo.setDate(alert.getDate().toString());
            avo.setLevel(alert.getLevel());
            avo.setRiskIndex(alert.getRiskIndex());
            alertVOs.add(avo);
        }

        TimeseriesVO vo = new TimeseriesVO();
        vo.setDates(dates);
        vo.setOilPrice(oilPrices);
        vo.setRiskIndex(riskIndices);
        vo.setAlerts(alertVOs);

        return vo;
    }

    @Override
    public Map<String, Object> getPredictionFromEngine() {
        return callPythonDaily();
    }

    @Override
    @SuppressWarnings("unchecked")
    public ModelSignalVO getModelSignals() {
        Map<String, Object> prediction = callPythonDaily();

        Map<String, Object> expertSignals = (Map<String, Object>) prediction.get("expert_signals");
        Map<String, Object> dashboard = (Map<String, Object>) prediction.get("dashboard");
        Map<String, Object> pred = (Map<String, Object>) prediction.get("prediction");

        ModelSignalVO vo = new ModelSignalVO();
        vo.setLstmPredPrice(toDouble(expertSignals.get("lstm_pred_price")));
        vo.setLstmDirection(mapDirection((String) expertSignals.get("lstm_direction")));
        vo.setLstmUpProb(toDouble(expertSignals.get("lstm_up_prob")));
        vo.setXgbRiskScore(toDouble(expertSignals.get("xgb_risk_score")));
        vo.setStackingReturnPct(toDouble(pred.get("predicted_return_pct")));
        vo.setStackingRiskZone(mapRiskZone((String) pred.get("risk_zone")));
        vo.setDate((String) dashboard.get("date"));

        return vo;
    }

    private Map<String, Object> callPythonDaily() {
        String url = pythonEngineUrl + "/predict/daily";
        try {
            ResponseEntity<Map<String, Object>> response = restTemplate.exchange(
                    url,
                    HttpMethod.POST,
                    null,
                    new ParameterizedTypeReference<>() {}
            );
            Map<String, Object> body = response.getBody();
            if (body == null) {
                throw new BusinessException(502, "Empty response from Python engine");
            }
            return body;
        } catch (RestClientException e) {
            log.error("Failed to call Python engine for daily prediction: {}", e.getMessage());
            throw new BusinessException(502, "Python prediction engine unavailable: " + e.getMessage());
        }
    }

    private static double toDouble(Object val) {
        if (val instanceof Number n) {
            return n.doubleValue();
        }
        return 0.0;
    }

    private static String mapDirection(String direction) {
        if (direction == null) return "Neutral";
        return switch (direction) {
            case "上升", "看涨", "上涨" -> "Up";
            case "下降", "看跌", "下跌" -> "Down";
            default -> direction;
        };
    }

    private static String mapRiskZone(String zone) {
        if (zone == null) return "Medium";
        return switch (zone) {
            case "高风险" -> "High";
            case "低风险" -> "Low";
            case "中风险" -> "Medium";
            default -> zone;
        };
    }
}
