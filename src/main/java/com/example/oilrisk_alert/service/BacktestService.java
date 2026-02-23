package com.example.oilrisk_alert.service;

import com.example.oilrisk_alert.dto.BacktestRequestDTO;
import com.example.oilrisk_alert.vo.BacktestResultVO;

public interface BacktestService {

    BacktestResultVO runBacktest(BacktestRequestDTO request);
}
