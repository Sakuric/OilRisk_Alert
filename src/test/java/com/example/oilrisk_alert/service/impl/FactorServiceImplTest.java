package com.example.oilrisk_alert.service.impl;

import com.example.oilrisk_alert.common.BusinessException;
import com.example.oilrisk_alert.config.WeightsConfig;
import com.example.oilrisk_alert.dto.WeightDTO;
import com.example.oilrisk_alert.entity.RiskFactor;
import com.example.oilrisk_alert.entity.RiskIndex;
import com.example.oilrisk_alert.mapper.FactorMapper;
import com.example.oilrisk_alert.mapper.RiskMapper;
import com.example.oilrisk_alert.vo.FactorVO;
import com.example.oilrisk_alert.vo.RadarScoreVO;
import com.example.oilrisk_alert.vo.WeightUpdateResultVO;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class FactorServiceImplTest {

    @Mock
    private FactorMapper factorMapper;

    @Mock
    private RiskMapper riskMapper;

    @Spy
    private WeightsConfig weightsConfig = new WeightsConfig();

    @InjectMocks
    private FactorServiceImpl factorService;

    private static final LocalDate TEST_DATE = LocalDate.of(2024, 4, 1);

    private List<RiskFactor> buildTestFactors() {
        return List.of(
                factor("crude_inventory", "原油库存变化率", "SUPPLY_DEMAND", -4.2, 0.12),
                factor("opec_output", "OPEC产量变化", "SUPPLY_DEMAND", -1.8, 0.09),
                factor("us_dollar_index", "美元指数", "MACRO", 104.5, -0.04),
                factor("cpi_yoy", "美国CPI同比", "MACRO", 3.5, 0.05),
                factor("brent_futures_basis", "布伦特期货基差", "FINANCIAL", 2.1, 0.07),
                factor("vix_index", "VIX恐慌指数", "FINANCIAL", 22.3, 0.06),
                factor("middle_east_tension", "中东紧张指数", "GEOPOLITICAL", 8.5, 0.13),
                factor("russia_ukraine_risk", "俄乌风险指数", "GEOPOLITICAL", 7.2, 0.11),
                factor("oil_sentiment_score", "石油市场情绪分", "SENTIMENT", 0.65, 0.04),
                factor("news_sentiment", "新闻情绪指数", "SENTIMENT", 0.45, 0.03)
        );
    }

    private RiskFactor factor(String name, String nameZh, String category, double value, double shap) {
        RiskFactor f = new RiskFactor();
        f.setDate(TEST_DATE);
        f.setFactorName(name);
        f.setFactorNameZh(nameZh);
        f.setCategory(category);
        f.setValue(BigDecimal.valueOf(value));
        f.setShapValue(BigDecimal.valueOf(shap));
        return f;
    }

    @Test
    void testGetRadar_returnsFiveDimensions() {
        when(factorMapper.findByDate(TEST_DATE)).thenReturn(buildTestFactors());

        List<RadarScoreVO> result = factorService.getRadarScores(TEST_DATE);

        assertEquals(5, result.size());
    }

    @Test
    void testGetRadar_categoriesCorrect() {
        when(factorMapper.findByDate(TEST_DATE)).thenReturn(buildTestFactors());

        List<RadarScoreVO> result = factorService.getRadarScores(TEST_DATE);

        Set<String> categories = result.stream()
                .map(RadarScoreVO::getCategory)
                .collect(Collectors.toSet());
        assertTrue(categories.contains("SUPPLY_DEMAND"));
        assertTrue(categories.contains("MACRO"));
        assertTrue(categories.contains("FINANCIAL"));
        assertTrue(categories.contains("GEOPOLITICAL"));
        assertTrue(categories.contains("SENTIMENT"));
    }

    @Test
    void testGetRadar_scoresNormalizedTo100() {
        when(factorMapper.findByDate(TEST_DATE)).thenReturn(buildTestFactors());

        List<RadarScoreVO> result = factorService.getRadarScores(TEST_DATE);

        double maxScore = result.stream()
                .mapToDouble(r -> r.getScore().doubleValue())
                .max().orElse(0);
        assertEquals(100.0, maxScore, 0.1);

        for (RadarScoreVO r : result) {
            assertTrue(r.getScore().doubleValue() >= 0);
            assertTrue(r.getScore().doubleValue() <= 100);
        }
    }

    @Test
    void testGetRadar_topFactorsPerCategory() {
        when(factorMapper.findByDate(TEST_DATE)).thenReturn(buildTestFactors());

        List<RadarScoreVO> result = factorService.getRadarScores(TEST_DATE);

        for (RadarScoreVO r : result) {
            assertNotNull(r.getTopFactors());
            assertTrue(r.getTopFactors().size() <= 3);
        }
    }

    @Test
    void testGetRadar_usesLatestDate_whenDateNull() {
        when(factorMapper.findLatestDate()).thenReturn(TEST_DATE);
        when(factorMapper.findByDate(TEST_DATE)).thenReturn(buildTestFactors());

        List<RadarScoreVO> result = factorService.getRadarScores(null);

        assertEquals(5, result.size());
    }

    @Test
    void testGetRadar_noData_throws404() {
        when(factorMapper.findLatestDate()).thenReturn(null);

        BusinessException ex = assertThrows(BusinessException.class,
                () -> factorService.getRadarScores(null));
        assertEquals(404, ex.getCode());
    }

    @Test
    void testGetExplain_returnsFactors() {
        when(factorMapper.findByDate(TEST_DATE)).thenReturn(buildTestFactors());

        List<FactorVO> result = factorService.getExplain(TEST_DATE);

        assertEquals(10, result.size());
        // Verify all factors are returned with correct fields
        assertNotNull(result.get(0).getName());
        assertNotNull(result.get(0).getCategory());
    }

    @Test
    void testGetExplain_dateNotFound_returnsEmpty() {
        when(factorMapper.findByDate(TEST_DATE)).thenReturn(Collections.emptyList());

        List<FactorVO> result = factorService.getExplain(TEST_DATE);

        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    void testUpdateWeights_recalculatesRiskIndex() {
        RiskIndex latest = new RiskIndex();
        latest.setDate(TEST_DATE);
        latest.setRiskIndex(BigDecimal.valueOf(55.0));
        latest.setRiskLevel("Medium");
        latest.setOilPrice(BigDecimal.valueOf(80.0));

        when(riskMapper.findLatest()).thenReturn(latest);
        when(factorMapper.findByDate(TEST_DATE)).thenReturn(buildTestFactors());
        when(factorMapper.findTopByDateOrderByAbsShap(any(), anyInt()))
                .thenReturn(buildTestFactors().subList(0, 5));

        WeightDTO dto = new WeightDTO();
        dto.setSupplyDemand(1.5);
        dto.setMacro(1.0);
        dto.setFinancial(1.0);
        dto.setGeopolitical(1.5);
        dto.setSentiment(0.5);

        WeightUpdateResultVO result = factorService.updateWeights(dto);

        assertNotNull(result.getRiskIndex());
        assertNotNull(result.getRiskLevel());
        assertNotNull(result.getRadarScores());
        assertEquals(5, result.getRadarScores().size());
        assertNotNull(result.getTopFactors());
        // With higher weights on high-SHAP categories, index should increase
        assertTrue(result.getRiskIndex().doubleValue() > 55.0);
    }

    @Test
    void testUpdateWeights_invalidRange_throws() {
        WeightDTO dto = new WeightDTO();
        dto.setSupplyDemand(3.0); // exceeds max 2.0
        dto.setMacro(1.0);
        dto.setFinancial(1.0);
        dto.setGeopolitical(1.0);
        dto.setSentiment(1.0);

        BusinessException ex = assertThrows(BusinessException.class,
                () -> factorService.updateWeights(dto));
        assertEquals(400, ex.getCode());
    }
}
