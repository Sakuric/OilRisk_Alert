package com.example.oilrisk_alert.controller;

import com.example.oilrisk_alert.service.ReportService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
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

    @GetMapping(value = "/risk/ai-summary", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter getAiSummary() {
        return reportService.generateAiSummary();
    }
}
