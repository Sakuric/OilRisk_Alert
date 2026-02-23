package com.example.oilrisk_alert.controller;

import com.example.oilrisk_alert.common.Result;
import com.example.oilrisk_alert.dto.BacktestRequestDTO;
import com.example.oilrisk_alert.service.BacktestService;
import com.example.oilrisk_alert.vo.BacktestResultVO;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class BacktestController {

    private final BacktestService backtestService;

    @PostMapping("/predict/backtest")
    public Result<BacktestResultVO> runBacktest(@RequestBody BacktestRequestDTO request) {
        return Result.success(backtestService.runBacktest(request));
    }
}
