package com.example.oilrisk_alert.service.impl;

import com.example.oilrisk_alert.common.BusinessException;
import com.example.oilrisk_alert.dto.BacktestRequestDTO;
import com.example.oilrisk_alert.service.BacktestService;
import com.example.oilrisk_alert.vo.BacktestResultVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class BacktestServiceImpl implements BacktestService {

    private final RestTemplate restTemplate;

    private static final Set<String> VALID_MODELS = Set.of("XGBoost", "LSTM", "Stacking");

    @Value("${python.engine.url}")
    private String pythonEngineUrl;

    @Override
    public BacktestResultVO runBacktest(BacktestRequestDTO request) {
        if (request.getStartDate() == null || request.getEndDate() == null) {
            throw new BusinessException(400, "startDate and endDate are required");
        }
        if (!request.getStartDate().isBefore(request.getEndDate())) {
            throw new BusinessException(400, "startDate must be before endDate");
        }
        if (request.getModel() == null || !VALID_MODELS.contains(request.getModel())) {
            throw new BusinessException(400, "model must be one of: XGBoost, LSTM, Stacking");
        }

        // Build request to Python engine
        Map<String, String> body = new HashMap<>();
        body.put("startDate", request.getStartDate().toString());
        body.put("endDate", request.getEndDate().toString());
        body.put("model", request.getModel());

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, String>> entity = new HttpEntity<>(body, headers);

        String url = pythonEngineUrl + "/predict/backtest";

        Map<String, Object> pyResult;
        try {
            ResponseEntity<Map<String, Object>> response = restTemplate.exchange(
                    url,
                    HttpMethod.POST,
                    entity,
                    new ParameterizedTypeReference<>() {}
            );
            pyResult = response.getBody();
        } catch (RestClientException e) {
            log.error("Failed to call Python engine: {}", e.getMessage());
            throw new BusinessException(502, "Python prediction engine unavailable: " + e.getMessage());
        }

        if (pyResult == null) {
            throw new BusinessException(502, "Empty response from Python engine");
        }

        // Map Python response to BacktestResultVO
        BacktestResultVO result = new BacktestResultVO();

        @SuppressWarnings("unchecked")
        List<String> dates = (List<String>) pyResult.get("dates");
        result.setDates(dates);

        @SuppressWarnings("unchecked")
        List<Number> actualRaw = (List<Number>) pyResult.get("actual");
        result.setActual(actualRaw.stream()
                .map(n -> BigDecimal.valueOf(n.doubleValue()).setScale(2, RoundingMode.HALF_UP))
                .collect(Collectors.toList()));

        @SuppressWarnings("unchecked")
        List<Number> predictedRaw = (List<Number>) pyResult.get("predicted");
        result.setPredicted(predictedRaw.stream()
                .map(n -> BigDecimal.valueOf(n.doubleValue()).setScale(2, RoundingMode.HALF_UP))
                .collect(Collectors.toList()));

        Number maeVal = (Number) pyResult.get("mae");
        result.setMae(BigDecimal.valueOf(maeVal.doubleValue()).setScale(2, RoundingMode.HALF_UP));

        Number hitRateVal = (Number) pyResult.get("hitRate");
        result.setHitRate(BigDecimal.valueOf(hitRateVal.doubleValue()).setScale(4, RoundingMode.HALF_UP));

        // falseAlarmRate = 1 - hitRate
        double hitRate = hitRateVal.doubleValue();
        result.setFalseAlarmRate(BigDecimal.valueOf(1.0 - hitRate).setScale(4, RoundingMode.HALF_UP));

        Number dirAccVal = (Number) pyResult.get("directionAccuracy");
        result.setDirectionAccuracy(BigDecimal.valueOf(dirAccVal.doubleValue()).setScale(4, RoundingMode.HALF_UP));

        return result;
    }
}
