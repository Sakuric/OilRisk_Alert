package com.example.oilrisk_alert.controller;

import com.example.oilrisk_alert.common.Result;
import com.example.oilrisk_alert.service.SystemStatusService;
import com.example.oilrisk_alert.vo.CollectResultVO;
import com.example.oilrisk_alert.vo.SystemStatusVO;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class SystemStatusController {

    private final SystemStatusService systemStatusService;

    @GetMapping("/system/status")
    public Result<SystemStatusVO> getSystemStatus() {
        return Result.success(systemStatusService.getSystemStatus());
    }

    @PostMapping("/collect/trigger")
    public Result<CollectResultVO> triggerCollection() {
        return Result.success(systemStatusService.triggerCollection());
    }

    @GetMapping("/collect/log")
    public Result<List<Map<String, Object>>> getCollectionLogs(
            @RequestParam(defaultValue = "20") int limit) {
        return Result.success(systemStatusService.getCollectionLogs(limit));
    }
}
