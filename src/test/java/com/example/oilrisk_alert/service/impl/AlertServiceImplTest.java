package com.example.oilrisk_alert.service.impl;

import com.example.oilrisk_alert.common.BusinessException;
import com.example.oilrisk_alert.dto.AlertQueryDTO;
import com.example.oilrisk_alert.entity.Alert;
import com.example.oilrisk_alert.mapper.AlertMapper;
import com.example.oilrisk_alert.vo.AlertDetailVO;
import com.example.oilrisk_alert.vo.AlertVO;
import com.example.oilrisk_alert.vo.PageVO;
import tools.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AlertServiceImplTest {

    @Mock
    private AlertMapper alertMapper;

    @Spy
    private ObjectMapper objectMapper = new ObjectMapper();

    @InjectMocks
    private AlertServiceImpl alertService;

    private Alert buildAlert(Long id) {
        Alert alert = new Alert();
        alert.setId(id);
        alert.setDate(LocalDate.of(2024, 4, 1));
        alert.setLevel("High");
        alert.setRiskIndex(BigDecimal.valueOf(78.5));
        alert.setTriggerType("THRESHOLD");
        alert.setTriggerFactor("middle_east_tension");
        alert.setTriggerFactorZh("中东紧张指数");
        alert.setSummary("中东地区紧张局势升级");
        alert.setSummaryEn("Middle East tensions escalated");
        return alert;
    }

    @Test
    void testGetAlerts_pagination() {
        when(alertMapper.countByLevel(null)).thenReturn(25L);
        when(alertMapper.findPage(anyInt(), anyInt(), any(), anyString(), anyString()))
                .thenReturn(List.of(buildAlert(1L), buildAlert(2L)));

        AlertQueryDTO query = new AlertQueryDTO();
        query.setPage(1);
        query.setSize(2);

        PageVO<AlertVO> result = alertService.getAlerts(query);

        assertEquals(25L, result.getTotal());
        assertEquals(1, result.getPage());
        assertEquals(2, result.getSize());
        assertEquals(2, result.getRecords().size());
    }

    @Test
    void testGetAlerts_filterByLevel() {
        when(alertMapper.countByLevel("High")).thenReturn(5L);
        when(alertMapper.findPage(anyInt(), anyInt(), eq("High"), anyString(), anyString()))
                .thenReturn(List.of(buildAlert(1L)));

        AlertQueryDTO query = new AlertQueryDTO();
        query.setLevel("High");

        PageVO<AlertVO> result = alertService.getAlerts(query);

        assertEquals(5L, result.getTotal());
        assertEquals("High", result.getRecords().get(0).getLevel());
    }

    @Test
    void testGetAlertDetail_found_withTriggerRules() {
        Alert alert = buildAlert(1L);
        alert.setDetail("[{\"ruleType\":\"THRESHOLD\",\"factor\":\"middle_east_tension\"," +
                "\"factorZh\":\"中东紧张指数\",\"currentValue\":8.5,\"threshold\":7.0," +
                "\"description\":\"中东紧张指数超过高风险阈值7.0\"}]");
        when(alertMapper.findById(1L)).thenReturn(alert);

        AlertDetailVO result = alertService.getAlertDetail(1L);

        assertEquals(1L, result.getId());
        assertEquals("High", result.getLevel());
        assertNotNull(result.getTriggerRules());
        assertEquals(1, result.getTriggerRules().size());
        assertEquals("THRESHOLD", result.getTriggerRules().get(0).getRuleType());
        assertEquals("middle_east_tension", result.getTriggerRules().get(0).getFactor());
        assertEquals(new BigDecimal("8.5"), result.getTriggerRules().get(0).getCurrentValue());
    }

    @Test
    void testGetAlertDetail_emptyDetail_returnsEmptyRules() {
        Alert alert = buildAlert(1L);
        alert.setDetail(null);
        when(alertMapper.findById(1L)).thenReturn(alert);

        AlertDetailVO result = alertService.getAlertDetail(1L);

        assertNotNull(result.getTriggerRules());
        assertTrue(result.getTriggerRules().isEmpty());
    }

    @Test
    void testGetAlertDetail_notFound_throws() {
        when(alertMapper.findById(999L)).thenReturn(null);

        BusinessException ex = assertThrows(BusinessException.class,
                () -> alertService.getAlertDetail(999L));
        assertEquals(404, ex.getCode());
    }

    @Test
    void testGetAlertDetail_invalidJson_returnsEmptyRules() {
        Alert alert = buildAlert(1L);
        alert.setDetail("not valid json");
        when(alertMapper.findById(1L)).thenReturn(alert);

        AlertDetailVO result = alertService.getAlertDetail(1L);

        assertNotNull(result.getTriggerRules());
        assertTrue(result.getTriggerRules().isEmpty());
    }
}
