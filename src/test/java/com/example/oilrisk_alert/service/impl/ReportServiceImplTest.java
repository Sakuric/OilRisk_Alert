package com.example.oilrisk_alert.service.impl;

import com.example.oilrisk_alert.common.BusinessException;
import com.example.oilrisk_alert.entity.Alert;
import com.example.oilrisk_alert.mapper.AlertMapper;
import tools.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.math.BigDecimal;
import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ReportServiceImplTest {

    @Mock
    private AlertMapper alertMapper;

    @Spy
    private ObjectMapper objectMapper = new ObjectMapper();

    @InjectMocks
    private ReportServiceImpl reportService;

    @Test
    void testGenerateReport_alertNotFound_throws() {
        when(alertMapper.findById(999L)).thenReturn(null);

        BusinessException ex = assertThrows(BusinessException.class,
                () -> reportService.generateReport(999L));
        assertEquals(404, ex.getCode());
    }

    @Test
    void testGenerateReport_cachedReport_returnsSseEmitter() {
        Alert alert = new Alert();
        alert.setId(1L);
        alert.setDate(LocalDate.of(2024, 4, 1));
        alert.setLevel("High");
        alert.setRiskIndex(BigDecimal.valueOf(78.5));
        alert.setTriggerFactorZh("中东紧张指数");
        alert.setAiReport("这是一段缓存的AI分析报告文本。");

        when(alertMapper.findById(1L)).thenReturn(alert);

        SseEmitter emitter = reportService.generateReport(1L);

        assertNotNull(emitter);
    }

    @Test
    void testGenerateReport_noApiKey_returnsMockEmitter() {
        Alert alert = new Alert();
        alert.setId(2L);
        alert.setDate(LocalDate.of(2024, 4, 1));
        alert.setLevel("High");
        alert.setRiskIndex(BigDecimal.valueOf(78.5));
        alert.setTriggerFactor("middle_east_tension");
        alert.setTriggerFactorZh("中东紧张指数");
        alert.setAiReport(null);

        when(alertMapper.findById(2L)).thenReturn(alert);

        // apiKey defaults to empty string (field injection), so mock path is used
        SseEmitter emitter = reportService.generateReport(2L);

        assertNotNull(emitter);
    }
}
