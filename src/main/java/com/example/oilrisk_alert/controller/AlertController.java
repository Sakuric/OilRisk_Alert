package com.example.oilrisk_alert.controller;

import com.example.oilrisk_alert.common.Result;
import com.example.oilrisk_alert.dto.AlertQueryDTO;
import com.example.oilrisk_alert.service.AlertService;
import com.example.oilrisk_alert.vo.AlertDetailVO;
import com.example.oilrisk_alert.vo.AlertVO;
import com.example.oilrisk_alert.vo.PageVO;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class AlertController {

    private final AlertService alertService;

    @GetMapping("/alerts")
    public Result<PageVO<AlertVO>> getAlerts(AlertQueryDTO query) {
        return Result.success(alertService.getAlerts(query));
    }

    @GetMapping("/alerts/{id}")
    public Result<AlertDetailVO> getAlertDetail(@PathVariable Long id) {
        return Result.success(alertService.getAlertDetail(id));
    }
}
