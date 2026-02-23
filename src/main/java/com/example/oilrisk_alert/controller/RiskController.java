package com.example.oilrisk_alert.controller;

import com.example.oilrisk_alert.common.Result;
import com.example.oilrisk_alert.dto.TimeseriesQueryDTO;
import com.example.oilrisk_alert.service.RiskService;
import com.example.oilrisk_alert.vo.RiskCurrentVO;
import com.example.oilrisk_alert.vo.TimeseriesVO;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class RiskController {

    private final RiskService riskService;

    @GetMapping("/risk/current")
    public Result<RiskCurrentVO> getCurrentRisk() {
        return Result.success(riskService.getCurrentRisk());
    }

    @GetMapping("/factors/timeseries")
    public Result<TimeseriesVO> getTimeseries(TimeseriesQueryDTO query) {
        return Result.success(riskService.getTimeseries(query.getStart(), query.getEnd()));
    }
}
