package com.example.oilrisk_alert.service.impl;

import com.example.oilrisk_alert.common.BusinessException;
import com.example.oilrisk_alert.common.RiskLevel;
import com.example.oilrisk_alert.config.WeightsConfig;
import com.example.oilrisk_alert.dto.WeightDTO;
import com.example.oilrisk_alert.entity.RiskFactor;
import com.example.oilrisk_alert.entity.RiskIndex;
import com.example.oilrisk_alert.mapper.FactorMapper;
import com.example.oilrisk_alert.mapper.RiskMapper;
import com.example.oilrisk_alert.service.FactorService;
import com.example.oilrisk_alert.vo.FactorVO;
import com.example.oilrisk_alert.vo.RadarScoreVO;
import com.example.oilrisk_alert.vo.WeightUpdateResultVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class FactorServiceImpl implements FactorService {

    private final FactorMapper factorMapper;
    private final RiskMapper riskMapper;
    private final WeightsConfig weightsConfig;
    private final RestTemplate restTemplate;

    @Value("${python.engine.url}")
    private String pythonEngineUrl;

    private static final List<String> CATEGORY_ORDER = List.of(
            "SUPPLY_DEMAND", "MACRO", "FINANCIAL", "GEOPOLITICAL", "SENTIMENT");

    // ── SHAP 缓存（5分钟过期）──

    private static class CachedShapResult {
        final String date;
        final double riskScore;
        final List<FactorVO> factors;
        final long timestamp;

        CachedShapResult(String date, double riskScore, List<FactorVO> factors) {
            this.date = date;
            this.riskScore = riskScore;
            this.factors = factors;
            this.timestamp = System.currentTimeMillis();
        }

        boolean isExpired() {
            return System.currentTimeMillis() - timestamp > 5 * 60 * 1000;
        }
    }

    private volatile CachedShapResult shapCache;

    // ── 调用 Python Engine /shap/factors ──

    @SuppressWarnings("unchecked")
    private CachedShapResult fetchRealShapFactors() {
        if (shapCache != null && !shapCache.isExpired()) {
            return shapCache;
        }

        String url = pythonEngineUrl + "/shap/factors";
        try {
            ResponseEntity<Map<String, Object>> response = restTemplate.exchange(
                    url, HttpMethod.GET, null,
                    new ParameterizedTypeReference<>() {});
            Map<String, Object> body = response.getBody();
            if (body == null) {
                throw new RestClientException("Empty response");
            }

            String date = (String) body.get("date");
            double riskScore = ((Number) body.get("riskScore")).doubleValue();
            List<Map<String, Object>> rawFactors = (List<Map<String, Object>>) body.get("factors");

            List<FactorVO> factors = new ArrayList<>();
            for (Map<String, Object> raw : rawFactors) {
                FactorVO vo = new FactorVO();
                vo.setName((String) raw.get("name"));
                vo.setNameZh((String) raw.get("nameZh"));
                vo.setShap(BigDecimal.valueOf(((Number) raw.get("shapValue")).doubleValue()));
                vo.setCategory((String) raw.get("category"));
                vo.setValue(BigDecimal.valueOf(((Number) raw.get("value")).doubleValue()));
                factors.add(vo);
            }

            CachedShapResult result = new CachedShapResult(date, riskScore, factors);
            shapCache = result;
            return result;
        } catch (RestClientException e) {
            log.warn("Failed to fetch SHAP factors from Python engine: {}", e.getMessage());
            return null;
        }
    }

    // ── 公共 API ──

    @Override
    public List<RadarScoreVO> getRadarScores(LocalDate date) {
        // 优先从 Python Engine 获取
        CachedShapResult shap = fetchRealShapFactors();
        if (shap != null) {
            return buildRadarFromFactors(shap.factors);
        }

        // Fallback: 数据库
        if (date == null) {
            date = factorMapper.findLatestDate();
        }
        if (date == null) {
            throw new BusinessException(404, "No factor data available");
        }

        List<RiskFactor> factors = factorMapper.findByDate(date);
        if (factors.isEmpty()) {
            throw new BusinessException(404, "No factor data for date: " + date);
        }

        List<FactorVO> factorVOs = factors.stream().map(this::toFactorVO).collect(Collectors.toList());
        return buildRadarFromFactors(factorVOs);
    }

    @Override
    public List<FactorVO> getExplain(LocalDate date) {
        // 优先从 Python Engine 获取
        CachedShapResult shap = fetchRealShapFactors();
        if (shap != null) {
            return shap.factors;
        }

        // Fallback: 数据库
        List<RiskFactor> factors = factorMapper.findByDate(date);
        return factors.stream().map(this::toFactorVO).collect(Collectors.toList());
    }

    @Override
    public WeightUpdateResultVO updateWeights(WeightDTO dto) {
        validateWeights(dto);

        weightsConfig.setSupplyDemand(dto.getSupplyDemand());
        weightsConfig.setMacro(dto.getMacro());
        weightsConfig.setFinancial(dto.getFinancial());
        weightsConfig.setGeopolitical(dto.getGeopolitical());
        weightsConfig.setSentiment(dto.getSentiment());

        // baseRiskIndex: 始终使用 DB riskIndex，与 getCurrentRisk() 保持一致
        // （Python Engine 的 riskScore 基于不同公式，直接用作 base 会导致权重调整后
        //  riskIndex 与初始展示值断层，用户看到的表现是：改权重后指数从 60 跳到 0）
        RiskIndex latest = riskMapper.findLatest();
        if (latest == null) {
            throw new BusinessException(404, "No risk data available");
        }
        double baseRiskIndex = latest.getRiskIndex().doubleValue();

        // SHAP 因子: 优先 Python Engine 实时数据，fallback 数据库
        List<FactorVO> allFactors;
        CachedShapResult shap = fetchRealShapFactors();
        if (shap != null) {
            allFactors = shap.factors;
        } else {
            List<RiskFactor> dbFactors = factorMapper.findByDate(latest.getDate());
            allFactors = dbFactors.stream().map(this::toFactorVO).collect(Collectors.toList());
        }

        // Recalculate adjusted risk index based on weighted SHAP deviation
        double totalWeightedShap = 0;
        double totalUnweightedShap = 0;
        for (FactorVO f : allFactors) {
            double absShap = Math.abs(f.getShap().doubleValue());
            double weight = weightsConfig.getWeight(f.getCategory());
            totalWeightedShap += absShap * weight;
            totalUnweightedShap += absShap;
        }

        double ratio = totalUnweightedShap == 0 ? 1.0 : totalWeightedShap / totalUnweightedShap;
        double adjustedIndex = Math.max(0, Math.min(100, baseRiskIndex * ratio));

        BigDecimal newRiskIndex = BigDecimal.valueOf(adjustedIndex)
                .setScale(2, RoundingMode.HALF_UP);

        List<RadarScoreVO> radarScores = buildRadarFromFactors(allFactors);
        List<FactorVO> topFactors = allFactors.stream()
                .sorted(Comparator.comparingDouble(
                        (FactorVO f) -> Math.abs(f.getShap().doubleValue())).reversed())
                .limit(5)
                .collect(Collectors.toList());

        WeightUpdateResultVO result = new WeightUpdateResultVO();
        result.setRiskIndex(newRiskIndex);
        result.setRiskLevel(RiskLevel.fromIndex(newRiskIndex).getLabel());
        result.setRadarScores(radarScores);
        result.setTopFactors(topFactors);
        return result;
    }

    // ── 内部方法 ──

    private List<RadarScoreVO> buildRadarFromFactors(List<FactorVO> allFactors) {
        Map<String, List<FactorVO>> grouped = allFactors.stream()
                .collect(Collectors.groupingBy(FactorVO::getCategory));

        Map<String, Double> rawScores = new LinkedHashMap<>();
        Map<String, List<FactorVO>> topFactorsMap = new LinkedHashMap<>();

        for (String category : CATEGORY_ORDER) {
            List<FactorVO> catFactors = grouped.getOrDefault(category, Collections.emptyList());
            if (catFactors.isEmpty()) {
                rawScores.put(category, 0.0);
                topFactorsMap.put(category, Collections.emptyList());
                continue;
            }

            // 按 |SHAP| 降序排列，取 top-3 求均值
            // 避免大量 SHAP≈0 的因子（如地缘政治 13 个中 8 个为 0）拉低均值
            List<FactorVO> sorted = catFactors.stream()
                    .sorted(Comparator.comparingDouble(
                            (FactorVO f) -> Math.abs(f.getShap().doubleValue())).reversed())
                    .collect(Collectors.toList());

            double topAvgAbsShap = sorted.stream()
                    .limit(3)
                    .mapToDouble(f -> Math.abs(f.getShap().doubleValue()))
                    .average()
                    .orElse(0.0);

            double weight = weightsConfig.getWeight(category);
            rawScores.put(category, topAvgAbsShap * weight);

            List<FactorVO> top3 = sorted.stream().limit(3).collect(Collectors.toList());
            topFactorsMap.put(category, top3);
        }

        double maxRaw = rawScores.values().stream()
                .mapToDouble(Double::doubleValue).max().orElse(1.0);
        if (maxRaw == 0) maxRaw = 1.0;

        List<RadarScoreVO> result = new ArrayList<>();
        for (String category : CATEGORY_ORDER) {
            Double raw = rawScores.get(category);
            if (raw == null) continue;

            RadarScoreVO vo = new RadarScoreVO();
            vo.setCategory(category);
            vo.setCategoryZh(WeightsConfig.getCategoryZh(category));
            vo.setScore(BigDecimal.valueOf(raw / maxRaw * 100).setScale(1, RoundingMode.HALF_UP));
            vo.setTopFactors(topFactorsMap.getOrDefault(category, Collections.emptyList()));
            result.add(vo);
        }

        return result;
    }

    private void validateWeights(WeightDTO dto) {
        if (dto.getSupplyDemand() < 0 || dto.getSupplyDemand() > 2) {
            throw new BusinessException(400, "supplyDemand weight must be between 0 and 2");
        }
        if (dto.getMacro() < 0 || dto.getMacro() > 2) {
            throw new BusinessException(400, "macro weight must be between 0 and 2");
        }
        if (dto.getFinancial() < 0 || dto.getFinancial() > 2) {
            throw new BusinessException(400, "financial weight must be between 0 and 2");
        }
        if (dto.getGeopolitical() < 0 || dto.getGeopolitical() > 2) {
            throw new BusinessException(400, "geopolitical weight must be between 0 and 2");
        }
        if (dto.getSentiment() < 0 || dto.getSentiment() > 2) {
            throw new BusinessException(400, "sentiment weight must be between 0 and 2");
        }
    }

    private FactorVO toFactorVO(RiskFactor f) {
        FactorVO vo = new FactorVO();
        vo.setName(f.getFactorName());
        vo.setNameZh(f.getFactorNameZh());
        vo.setShap(f.getShapValue());
        vo.setCategory(f.getCategory());
        vo.setValue(f.getValue());
        return vo;
    }

    @Override
    public List<Map<String, Object>> getWeightHistory(int months) {
        LocalDate end = LocalDate.now();
        LocalDate start = end.minusMonths(months);

        // 查询按日期+分类聚合的SHAP绝对值总和
        List<Map<String, Object>> rawRows = factorMapper.findWeightHistory(start, end);
        if (rawRows == null || rawRows.isEmpty()) {
            return Collections.emptyList();
        }

        // 按日期分组: {date -> {category -> totalShap}}
        Map<String, Map<String, Double>> dateMap = new LinkedHashMap<>();
        for (Map<String, Object> row : rawRows) {
            String dateStr = String.valueOf(row.get("date"));
            String category = String.valueOf(row.get("category"));
            double shap = row.get("total_shap") != null
                    ? ((Number) row.get("total_shap")).doubleValue() : 0.0;
            dateMap.computeIfAbsent(dateStr, k -> new LinkedHashMap<>()).put(category, shap);
        }

        // 转为百分比格式的列表
        List<Map<String, Object>> result = new ArrayList<>();
        Map<String, String> categoryKeyMap = Map.of(
                "SUPPLY_DEMAND", "supplyDemand",
                "MACRO", "macro",
                "FINANCIAL", "financial",
                "GEOPOLITICAL", "geopolitical",
                "SENTIMENT", "sentiment"
        );

        for (Map.Entry<String, Map<String, Double>> entry : dateMap.entrySet()) {
            Map<String, Double> cats = entry.getValue();
            double total = cats.values().stream().mapToDouble(Double::doubleValue).sum();
            if (total <= 0) continue;

            Map<String, Object> point = new LinkedHashMap<>();
            point.put("date", entry.getKey());
            for (Map.Entry<String, String> cm : categoryKeyMap.entrySet()) {
                double raw = cats.getOrDefault(cm.getKey(), 0.0);
                point.put(cm.getValue(), Math.round(raw / total * 10000.0) / 100.0);
            }
            result.add(point);
        }

        return result;
    }
}
