package com.example.oilrisk_alert.service.impl;

import com.example.oilrisk_alert.common.BusinessException;
import com.example.oilrisk_alert.service.SystemStatusService;
import com.example.oilrisk_alert.vo.CollectResultVO;
import com.example.oilrisk_alert.vo.SystemStatusVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class SystemStatusServiceImpl implements SystemStatusService {

    private final RestTemplate restTemplate;

    @Value("${python.engine.url}")
    private String pythonEngineUrl;

    @Override
    @SuppressWarnings("unchecked")
    public SystemStatusVO getSystemStatus() {
        String url = pythonEngineUrl + "/collect/status";
        try {
            ResponseEntity<Map<String, Object>> response = restTemplate.exchange(
                    url,
                    HttpMethod.GET,
                    null,
                    new ParameterizedTypeReference<>() {}
            );
            Map<String, Object> body = response.getBody();
            if (body == null) {
                throw new BusinessException(502, "Empty response from Python engine");
            }

            SystemStatusVO vo = new SystemStatusVO();
            vo.setLastCollectionTime(getString(body, "last_collection_time"));
            vo.setLastCollectionStatus(getString(body, "last_collection_status"));
            vo.setLastPredictionTime(getString(body, "last_prediction_time"));
            vo.setDataDate(getString(body, "data_date"));
            vo.setNextScheduled(getString(body, "next_scheduled"));

            // 解析因子覆盖率
            Object coverageObj = body.get("factors_coverage");
            if (coverageObj instanceof Map<?, ?> coverageMap) {
                Map<String, SystemStatusVO.FactorCoverageVO> coverage = new HashMap<>();
                for (Map.Entry<?, ?> entry : coverageMap.entrySet()) {
                    String freq = String.valueOf(entry.getKey());
                    if (entry.getValue() instanceof Map<?, ?> freqMap) {
                        SystemStatusVO.FactorCoverageVO fcvo = new SystemStatusVO.FactorCoverageVO();
                        fcvo.setTotal(toInt(freqMap.get("total")));
                        fcvo.setAvailable(toInt(freqMap.get("available")));
                        coverage.put(freq, fcvo);
                    }
                }
                vo.setFactorsCoverage(coverage);
            }

            return vo;
        } catch (RestClientException e) {
            log.error("Failed to get system status from Python engine: {}", e.getMessage());
            // 返回默认状态而非抛异常，因为 Python 端可能未启动采集模块
            SystemStatusVO vo = new SystemStatusVO();
            vo.setLastCollectionStatus("UNAVAILABLE");
            vo.setFactorsCoverage(Collections.emptyMap());
            return vo;
        }
    }

    @Override
    @SuppressWarnings("unchecked")
    public CollectResultVO triggerCollection() {
        String url = pythonEngineUrl + "/collect/trigger";
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

            CollectResultVO vo = new CollectResultVO();
            vo.setStatus(getString(body, "status").toLowerCase());
            vo.setMessage(getString(body, "message"));

            // 异步模式下 collection/prediction 字段为空，前端通过轮询 status 获取结果
            Object collObj = body.get("collection");
            if (collObj instanceof Map<?, ?> collMap) {
                CollectResultVO.CollectionDetail detail = new CollectResultVO.CollectionDetail();
                detail.setDate(getString(collMap, "date"));
                detail.setTotal(toInt(collMap.get("total")));
                detail.setSuccess(toInt(collMap.get("success")));
                detail.setFailed(toInt(collMap.get("failed")));
                detail.setDurationMs(toInt(collMap.get("duration_ms")));
                Object failedFactors = collMap.get("failed_factors");
                if (failedFactors instanceof List<?> failedList) {
                    detail.setFailedFactors(failedList.stream()
                            .map(String::valueOf)
                            .toList());
                }
                vo.setCollection(detail);
            }

            Object predObj = body.get("prediction");
            if (predObj instanceof Map<?, ?> predMap) {
                CollectResultVO.PredictionSummary pred = new CollectResultVO.PredictionSummary();
                pred.setScore(toDouble(predMap.get("score")));
                pred.setLevel(getString(predMap, "level"));
                pred.setDate(getString(predMap, "date"));
                vo.setPrediction(pred);
            }

            return vo;
        } catch (RestClientException e) {
            log.error("Failed to trigger collection: {}", e.getMessage());
            throw new BusinessException(502, "Python engine unavailable: " + e.getMessage());
        }
    }

    @Override
    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> getCollectionLogs(int limit) {
        String url = pythonEngineUrl + "/collect/log?limit=" + limit;
        try {
            ResponseEntity<List<Map<String, Object>>> response = restTemplate.exchange(
                    url,
                    HttpMethod.GET,
                    null,
                    new ParameterizedTypeReference<>() {}
            );
            List<Map<String, Object>> body = response.getBody();
            if (body == null) {
                return Collections.emptyList();
            }
            // 转换 snake_case → camelCase
            List<Map<String, Object>> result = new java.util.ArrayList<>(body.size());
            for (Map<String, Object> log : body) {
                Map<String, Object> mapped = new HashMap<>();
                mapped.put("id", log.get("id"));
                mapped.put("runDate", log.get("run_date"));
                mapped.put("source", log.get("source"));
                mapped.put("status", log.get("status"));
                mapped.put("factorsTotal", log.get("factors_total"));
                mapped.put("factorsOk", log.get("factors_ok"));
                mapped.put("factorsFailed", log.get("factors_failed"));
                mapped.put("errorDetail", log.get("error_detail"));
                mapped.put("durationMs", log.get("duration_ms"));
                mapped.put("createdAt", log.get("created_at"));
                result.add(mapped);
            }
            return result;
        } catch (RestClientException e) {
            log.error("Failed to get collection logs: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    private static String getString(Map<?, ?> map, String key) {
        Object val = map.get(key);
        return val != null ? String.valueOf(val) : "";
    }

    private static int toInt(Object val) {
        if (val instanceof Number n) {
            return n.intValue();
        }
        return 0;
    }

    private static double toDouble(Object val) {
        if (val instanceof Number n) {
            return n.doubleValue();
        }
        return 0.0;
    }
}
