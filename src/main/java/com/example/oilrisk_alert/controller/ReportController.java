package com.example.oilrisk_alert.controller;

import com.example.oilrisk_alert.service.ReportService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class ReportController {

    private final ReportService reportService;

    @GetMapping(value = "/report/{alertId}", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter getReport(@PathVariable Long alertId) {
        return reportService.generateReport(alertId);
    }
}
