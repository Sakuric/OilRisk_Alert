package com.example.oilrisk_alert;

import com.example.oilrisk_alert.common.BusinessException;
import com.example.oilrisk_alert.service.FactorService;
import com.example.oilrisk_alert.vo.FactorVO;
import com.example.oilrisk_alert.vo.RadarScoreVO;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@Transactional
class FactorServiceTest {

    @Autowired
    private FactorService factorService;

    @Test
    void testGetRadar_returnsFiveDimensions() {
        List<RadarScoreVO> result = factorService.getRadarScores(null);
        assertEquals(5, result.size());
    }

    @Test
    void testGetRadar_allCategoriesPresent() {
        List<RadarScoreVO> result = factorService.getRadarScores(null);
        Set<String> categories = result.stream()
                .map(RadarScoreVO::getCategory)
                .collect(Collectors.toSet());
        assertEquals(
                Set.of("SUPPLY_DEMAND", "MACRO", "FINANCIAL", "GEOPOLITICAL", "SENTIMENT"),
                categories);
    }

    @Test
    void testGetExplain_validDate() {
        // 2024-04-01 has risk_factor data in data.sql
        List<FactorVO> result = factorService.getExplain(LocalDate.of(2024, 4, 1));
        assertNotNull(result);
        assertFalse(result.isEmpty());
    }

    @Test
    void testGetExplain_invalidDate_returnsEmpty() {
        List<FactorVO> result = factorService.getExplain(LocalDate.of(1999, 1, 1));
        assertNotNull(result);
        assertTrue(result.isEmpty());
    }
}
