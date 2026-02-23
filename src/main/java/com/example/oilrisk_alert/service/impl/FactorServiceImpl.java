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
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class FactorServiceImpl implements FactorService {

    private final FactorMapper factorMapper;
    private final RiskMapper riskMapper;
    private final WeightsConfig weightsConfig;

    private static final List<String> CATEGORY_ORDER = List.of(
            "SUPPLY_DEMAND", "MACRO", "FINANCIAL", "GEOPOLITICAL", "SENTIMENT");

    @Override
    public List<RadarScoreVO> getRadarScores(LocalDate date) {
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

        Map<String, List<RiskFactor>> grouped = factors.stream()
                .collect(Collectors.groupingBy(RiskFactor::getCategory));

        Map<String, Double> rawScores = new LinkedHashMap<>();
        Map<String, List<FactorVO>> topFactorsMap = new LinkedHashMap<>();

        for (String category : CATEGORY_ORDER) {
            List<RiskFactor> catFactors = grouped.getOrDefault(category, Collections.emptyList());
            if (catFactors.isEmpty()) {
                rawScores.put(category, 0.0);
                topFactorsMap.put(category, Collections.emptyList());
                continue;
            }

            double avgAbsShap = catFactors.stream()
                    .mapToDouble(f -> Math.abs(f.getShapValue().doubleValue()))
                    .average()
                    .orElse(0.0);

            double weight = weightsConfig.getWeight(category);
            rawScores.put(category, avgAbsShap * weight);

            List<FactorVO> top3 = catFactors.stream()
                    .sorted(Comparator.comparingDouble(
                            (RiskFactor f) -> Math.abs(f.getShapValue().doubleValue())).reversed())
                    .limit(3)
                    .map(this::toFactorVO)
                    .collect(Collectors.toList());
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

    @Override
    public List<FactorVO> getExplain(LocalDate date) {
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

        RiskIndex latest = riskMapper.findLatest();
        if (latest == null) {
            throw new BusinessException(404, "No risk data available");
        }

        LocalDate latestDate = latest.getDate();
        List<RiskFactor> factors = factorMapper.findByDate(latestDate);

        // Recalculate adjusted risk index based on weighted SHAP deviation
        double totalWeightedShap = 0;
        double totalUnweightedShap = 0;
        for (RiskFactor f : factors) {
            double absShap = Math.abs(f.getShapValue().doubleValue());
            double weight = weightsConfig.getWeight(f.getCategory());
            totalWeightedShap += absShap * weight;
            totalUnweightedShap += absShap;
        }

        double ratio = totalUnweightedShap == 0 ? 1.0 : totalWeightedShap / totalUnweightedShap;
        double adjustedIndex = Math.max(0, Math.min(100,
                latest.getRiskIndex().doubleValue() * ratio));

        BigDecimal newRiskIndex = BigDecimal.valueOf(adjustedIndex)
                .setScale(2, RoundingMode.HALF_UP);

        List<RadarScoreVO> radarScores = getRadarScores(latestDate);
        List<FactorVO> topFactors = factorMapper.findTopByDateOrderByAbsShap(latestDate, 5)
                .stream().map(this::toFactorVO).collect(Collectors.toList());

        WeightUpdateResultVO result = new WeightUpdateResultVO();
        result.setRiskIndex(newRiskIndex);
        result.setRiskLevel(RiskLevel.fromIndex(newRiskIndex).getLabel());
        result.setRadarScores(radarScores);
        result.setTopFactors(topFactors);
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
        return vo;
    }
}
