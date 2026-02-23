package com.example.oilrisk_alert;

import com.example.oilrisk_alert.common.BusinessException;
import com.example.oilrisk_alert.dto.BacktestRequestDTO;
import com.example.oilrisk_alert.entity.RiskIndex;
import com.example.oilrisk_alert.mapper.RiskMapper;
import com.example.oilrisk_alert.service.impl.BacktestServiceImpl;
import com.example.oilrisk_alert.vo.BacktestResultVO;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class BacktestServiceTest {

    @Mock
    private RiskMapper riskMapper;

    @InjectMocks
    private BacktestServiceImpl backtestService;

    private List<RiskIndex> createMockData(int count) {
        List<RiskIndex> data = new ArrayList<>();
        LocalDate start = LocalDate.of(2024, 1, 1);
        for (int i = 0; i < count; i++) {
            RiskIndex ri = new RiskIndex();
            ri.setId((long) (i + 1));
            ri.setDate(start.plusMonths(i));
            ri.setOilPrice(BigDecimal.valueOf(70 + i * 2));
            ri.setRiskIndex(BigDecimal.valueOf(45 + i * 3));
            ri.setRiskLevel(ri.getRiskIndex().compareTo(new BigDecimal("70")) >= 0 ? "High" :
                    ri.getRiskIndex().compareTo(new BigDecimal("40")) >= 0 ? "Medium" : "Low");
            data.add(ri);
        }
        return data;
    }

    private BacktestRequestDTO createRequest(String model) {
        BacktestRequestDTO request = new BacktestRequestDTO();
        request.setStartDate(LocalDate.of(2024, 1, 1));
        request.setEndDate(LocalDate.of(2024, 10, 1));
        request.setModel(model);
        return request;
    }

    @Test
    void testBacktest_xgboost() {
        List<RiskIndex> mockData = createMockData(10);
        when(riskMapper.findByDateRange(any(), any())).thenReturn(mockData);

        BacktestResultVO result = backtestService.runBacktest(createRequest("XGBoost"));

        assertEquals(10, result.getDates().size());
        assertEquals(10, result.getActual().size());
        assertEquals(10, result.getPredicted().size());
        assertNotNull(result.getHitRate());
        assertNotNull(result.getFalseAlarmRate());
        assertNotNull(result.getMae());
        assertNotNull(result.getDirectionAccuracy());
    }

    @Test
    void testBacktest_differentModelsGiveDifferentPredictions() {
        List<RiskIndex> mockData = createMockData(10);
        when(riskMapper.findByDateRange(any(), any())).thenReturn(mockData);

        BacktestResultVO xgbResult = backtestService.runBacktest(createRequest("XGBoost"));
        BacktestResultVO arimaResult = backtestService.runBacktest(createRequest("ARIMA"));

        assertNotEquals(xgbResult.getPredicted(), arimaResult.getPredicted(),
                "Different models should produce different predicted values");
    }

    @Test
    void testBacktest_invalidModel_throwsException() {
        assertThrows(BusinessException.class, () ->
                backtestService.runBacktest(createRequest("InvalidModel")));
    }
}
