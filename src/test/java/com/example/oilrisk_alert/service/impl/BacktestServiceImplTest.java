package com.example.oilrisk_alert.service.impl;

import com.example.oilrisk_alert.common.BusinessException;
import com.example.oilrisk_alert.dto.BacktestRequestDTO;
import com.example.oilrisk_alert.entity.RiskIndex;
import com.example.oilrisk_alert.mapper.RiskMapper;
import com.example.oilrisk_alert.vo.BacktestResultVO;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class BacktestServiceImplTest {

    @Mock
    private RiskMapper riskMapper;

    @InjectMocks
    private BacktestServiceImpl backtestService;

    private List<RiskIndex> buildTestData() {
        List<RiskIndex> data = new ArrayList<>();
        LocalDate start = LocalDate.of(2024, 1, 1);
        double[] prices = {78.5, 80.2, 76.1, 82.3, 79.8};
        double[] riskIndices = {45.0, 52.0, 38.0, 68.0, 55.0};
        String[] levels = {"Medium", "Medium", "Low", "Medium", "Medium"};

        for (int i = 0; i < prices.length; i++) {
            RiskIndex ri = new RiskIndex();
            ri.setDate(start.plusMonths(i));
            ri.setOilPrice(BigDecimal.valueOf(prices[i]));
            ri.setRiskIndex(BigDecimal.valueOf(riskIndices[i]));
            ri.setRiskLevel(levels[i]);
            data.add(ri);
        }
        return data;
    }

    @Test
    void testBacktest_xgboost_returnsValidData() {
        when(riskMapper.findByDateRange(any(), any())).thenReturn(buildTestData());

        BacktestRequestDTO request = new BacktestRequestDTO();
        request.setStartDate(LocalDate.of(2024, 1, 1));
        request.setEndDate(LocalDate.of(2024, 6, 1));
        request.setModel("XGBoost");

        BacktestResultVO result = backtestService.runBacktest(request);

        assertEquals(5, result.getDates().size());
        assertEquals(5, result.getActual().size());
        assertEquals(5, result.getPredicted().size());
        assertNotNull(result.getMae());
        assertNotNull(result.getHitRate());
        assertNotNull(result.getFalseAlarmRate());
        assertNotNull(result.getDirectionAccuracy());

        // MAE should be reasonable (within perturbation range)
        assertTrue(result.getMae().doubleValue() < 10.0);

        // Hit rate + false alarm rate = 1.0
        double sum = result.getHitRate().doubleValue() + result.getFalseAlarmRate().doubleValue();
        assertEquals(1.0, sum, 0.0001);
    }

    @Test
    void testBacktest_allModels_returnDifferentPredictions() {
        when(riskMapper.findByDateRange(any(), any())).thenReturn(buildTestData());

        BacktestRequestDTO req = new BacktestRequestDTO();
        req.setStartDate(LocalDate.of(2024, 1, 1));
        req.setEndDate(LocalDate.of(2024, 6, 1));

        req.setModel("XGBoost");
        BacktestResultVO xgb = backtestService.runBacktest(req);

        req.setModel("ARIMA");
        BacktestResultVO arima = backtestService.runBacktest(req);

        req.setModel("LSTM");
        BacktestResultVO lstm = backtestService.runBacktest(req);

        // Different models should produce different predictions
        assertNotEquals(xgb.getPredicted().get(0), arima.getPredicted().get(0));
        assertNotEquals(xgb.getPredicted().get(0), lstm.getPredicted().get(0));
    }

    @Test
    void testBacktest_reproducible() {
        when(riskMapper.findByDateRange(any(), any())).thenReturn(buildTestData());

        BacktestRequestDTO req = new BacktestRequestDTO();
        req.setStartDate(LocalDate.of(2024, 1, 1));
        req.setEndDate(LocalDate.of(2024, 6, 1));
        req.setModel("XGBoost");

        BacktestResultVO first = backtestService.runBacktest(req);
        BacktestResultVO second = backtestService.runBacktest(req);

        // Same input should produce same output (date-seeded random)
        assertEquals(first.getPredicted(), second.getPredicted());
        assertEquals(first.getMae(), second.getMae());
    }

    @Test
    void testBacktest_dateRangeValidation() {
        BacktestRequestDTO req = new BacktestRequestDTO();
        req.setStartDate(LocalDate.of(2024, 6, 1));
        req.setEndDate(LocalDate.of(2024, 1, 1)); // end before start
        req.setModel("XGBoost");

        BusinessException ex = assertThrows(BusinessException.class,
                () -> backtestService.runBacktest(req));
        assertEquals(400, ex.getCode());
    }

    @Test
    void testBacktest_invalidModel_throws() {
        BacktestRequestDTO req = new BacktestRequestDTO();
        req.setStartDate(LocalDate.of(2024, 1, 1));
        req.setEndDate(LocalDate.of(2024, 6, 1));
        req.setModel("InvalidModel");

        BusinessException ex = assertThrows(BusinessException.class,
                () -> backtestService.runBacktest(req));
        assertEquals(400, ex.getCode());
    }

    @Test
    void testBacktest_noData_throws() {
        when(riskMapper.findByDateRange(any(), any())).thenReturn(Collections.emptyList());

        BacktestRequestDTO req = new BacktestRequestDTO();
        req.setStartDate(LocalDate.of(2024, 1, 1));
        req.setEndDate(LocalDate.of(2024, 6, 1));
        req.setModel("XGBoost");

        BusinessException ex = assertThrows(BusinessException.class,
                () -> backtestService.runBacktest(req));
        assertEquals(404, ex.getCode());
    }

    @Test
    void testBacktest_nullDates_throws() {
        BacktestRequestDTO req = new BacktestRequestDTO();
        req.setModel("XGBoost");

        BusinessException ex = assertThrows(BusinessException.class,
                () -> backtestService.runBacktest(req));
        assertEquals(400, ex.getCode());
    }
}
