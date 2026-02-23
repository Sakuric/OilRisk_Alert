package com.example.oilrisk_alert;

import com.example.oilrisk_alert.common.BusinessException;
import com.example.oilrisk_alert.service.AlertService;
import com.example.oilrisk_alert.vo.AlertDetailVO;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@Transactional
class AlertServiceTest {

    @Autowired
    private AlertService alertService;

    @Test
    void testGetAlertDetail_found() {
        // First alert in data.sql (id auto-generated, starts at 1)
        AlertDetailVO detail = alertService.getAlertDetail(1L);
        assertNotNull(detail);
        assertNotNull(detail.getTriggerRules());
        assertFalse(detail.getTriggerRules().isEmpty(),
                "Alert with detail JSON should have parsed trigger rules");
        assertNotNull(detail.getLevel());
        assertTrue(List.of("Low", "Medium", "High").contains(detail.getLevel()),
                "Level must be a valid risk level");
    }

    @Test
    void testGetAlertDetail_notFound() {
        assertThrows(BusinessException.class, () ->
                alertService.getAlertDetail(99999L));
    }
}
