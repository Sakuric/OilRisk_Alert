package com.example.oilrisk_alert.controller;

import com.example.oilrisk_alert.common.Result;
import com.example.oilrisk_alert.dto.WeightDTO;
import com.example.oilrisk_alert.service.FactorService;
import com.example.oilrisk_alert.vo.FactorVO;
import com.example.oilrisk_alert.vo.RadarScoreVO;
import com.example.oilrisk_alert.vo.WeightUpdateResultVO;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class FactorController {

    private final FactorService factorService;

    @GetMapping("/risk/radar")
    public Result<List<RadarScoreVO>> getRadarScores(
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate date) {
        return Result.success(factorService.getRadarScores(date));
    }

    @GetMapping("/explain/{date}")
    public Result<List<FactorVO>> getExplain(
            @PathVariable @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate date) {
        return Result.success(factorService.getExplain(date));
    }

    @PutMapping("/config/weights")
    public Result<WeightUpdateResultVO> updateWeights(@RequestBody WeightDTO dto) {
        return Result.success(factorService.updateWeights(dto));
    }
}
