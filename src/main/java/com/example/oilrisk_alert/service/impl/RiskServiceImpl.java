package com.example.oilrisk_alert.service.impl;

import com.example.oilrisk_alert.common.BusinessException;
import com.example.oilrisk_alert.entity.Alert;
import com.example.oilrisk_alert.entity.RiskFactor;
import com.example.oilrisk_alert.entity.RiskIndex;
import com.example.oilrisk_alert.mapper.AlertMapper;
import com.example.oilrisk_alert.mapper.FactorMapper;
import com.example.oilrisk_alert.mapper.RiskMapper;
import com.example.oilrisk_alert.service.RiskService;
import com.example.oilrisk_alert.util.LttbUtil;
import com.example.oilrisk_alert.vo.*;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Service
@RequiredArgsConstructor
public class RiskServiceImpl implements RiskService {

    private final RiskMapper riskMapper;
    private final FactorMapper factorMapper;
    private final AlertMapper alertMapper;

    private static final int LTTB_THRESHOLD = 2000;

    @Override
    public RiskCurrentVO getCurrentRisk() {
        RiskIndex latest = riskMapper.findLatest();
        if (latest == null) {
            throw new BusinessException(404, "No risk data available");
        }

        List<RiskFactor> topFactors = factorMapper.findTopByDateOrderByAbsShap(latest.getDate(), 5);

        RiskCurrentVO vo = new RiskCurrentVO();
        vo.setRiskIndex(latest.getRiskIndex());
        vo.setRiskLevel(latest.getRiskLevel());
        vo.setDate(latest.getDate().toString());

        List<FactorVO> factorVOs = new ArrayList<>();
        for (RiskFactor rf : topFactors) {
            FactorVO fv = new FactorVO();
            fv.setName(rf.getFactorName());
            fv.setNameZh(rf.getFactorNameZh());
            fv.setShap(rf.getShapValue());
            fv.setCategory(rf.getCategory());
            factorVOs.add(fv);
        }
        vo.setTopFactors(factorVOs);

        return vo;
    }

    @Override
    public TimeseriesVO getTimeseries(LocalDate start, LocalDate end) {
        // BR-02: default to last 2 years
        if (end == null) {
            end = LocalDate.now();
        }
        if (start == null) {
            start = end.minusYears(2);
        }

        List<RiskIndex> riskData = riskMapper.findByDateRange(start, end);
        List<Alert> alertData = alertMapper.findByDateRange(start, end);

        // Prepare raw data arrays
        List<String> dates = new ArrayList<>(riskData.size());
        List<BigDecimal> oilPrices = new ArrayList<>(riskData.size());
        List<BigDecimal> riskIndices = new ArrayList<>(riskData.size());

        for (RiskIndex ri : riskData) {
            dates.add(ri.getDate().toString());
            oilPrices.add(ri.getOilPrice());
            riskIndices.add(ri.getRiskIndex());
        }

        // LTTB downsampling if >2000 points
        if (riskData.size() > LTTB_THRESHOLD) {
            // Build [index, value] pairs for LTTB
            List<double[]> oilPriceData = new ArrayList<>(riskData.size());
            List<double[]> riskIndexData = new ArrayList<>(riskData.size());
            for (int i = 0; i < riskData.size(); i++) {
                oilPriceData.add(new double[]{i, oilPrices.get(i).doubleValue()});
                riskIndexData.add(new double[]{i, riskIndices.get(i).doubleValue()});
            }

            List<double[]> sampledOil = LttbUtil.downsample(oilPriceData, LTTB_THRESHOLD);
            List<double[]> sampledRisk = LttbUtil.downsample(riskIndexData, LTTB_THRESHOLD);

            // Collect all unique indices from both downsampled sets
            java.util.Set<Integer> indexSet = new java.util.TreeSet<>();
            for (double[] p : sampledOil) indexSet.add((int) p[0]);
            for (double[] p : sampledRisk) indexSet.add((int) p[0]);

            List<String> newDates = new ArrayList<>();
            List<BigDecimal> newOilPrices = new ArrayList<>();
            List<BigDecimal> newRiskIndices = new ArrayList<>();
            for (int idx : indexSet) {
                newDates.add(dates.get(idx));
                newOilPrices.add(oilPrices.get(idx));
                newRiskIndices.add(riskIndices.get(idx));
            }
            dates = newDates;
            oilPrices = newOilPrices;
            riskIndices = newRiskIndices;
        }

        // Build alert markers
        List<AlertTimeseriesVO> alertVOs = new ArrayList<>();
        for (Alert alert : alertData) {
            AlertTimeseriesVO avo = new AlertTimeseriesVO();
            avo.setDate(alert.getDate().toString());
            avo.setLevel(alert.getLevel());
            avo.setRiskIndex(alert.getRiskIndex());
            alertVOs.add(avo);
        }

        TimeseriesVO vo = new TimeseriesVO();
        vo.setDates(dates);
        vo.setOilPrice(oilPrices);
        vo.setRiskIndex(riskIndices);
        vo.setAlerts(alertVOs);

        return vo;
    }
}
