package com.example.oilrisk_alert.controller;

import com.example.oilrisk_alert.common.Result;
import com.example.oilrisk_alert.service.LlmConfigService;
import com.example.oilrisk_alert.vo.LlmConfigVO;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/config")
@RequiredArgsConstructor
public class LlmConfigController {

    private final LlmConfigService llmConfigService;

    @GetMapping("/llm")
    public Result<LlmConfigVO> getLlmConfig() {
        return Result.success(llmConfigService.getConfig());
    }

    @PutMapping("/llm")
    public Result<LlmConfigVO> updateLlmConfig(@RequestBody LlmConfigVO request) {
        return Result.success(llmConfigService.updateConfig(request));
    }
}
