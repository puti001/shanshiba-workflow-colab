# 海洋未來式：發燒的海洋母親 (ocean_future_ep01)

本專案使用 `shanshiba-workflow` V3 黃金標準管線建立。

## 標準製片 5 步驟：

1. **準備素材**：
   - 首尾幀放置於 `out/first/`、`out/last/`
   - 角色參考音置於 `out/voice/`
   - 編輯 `film.json` 確認分鏡、台詞與動作

2. **生成前防呆檢查 (Pre-flight Lint)**：
   ```powershell
   python lint_v3.py
   python build_specs_v3.py
   ```

3. **Colab G4 渲染 (14 步)**：
   ```powershell
   cd ../..
   python cloud/colab_h3.py check
   python cloud/colab_h3.py start --h3-only
   python cloud/colab_h3.py batch pipeline/ocean_future_ep01/out/h3/S01/spec.json ...
   python cloud/colab_h3.py stop   # ⚠️ 跑完務必關機！
   cd pipeline/ocean_future_ep01
   ```

4. **抽幀檢視與精準剪輯 (Tight Edit)**：
   ```powershell
   python make_ending_v3.py
   python fix_v3_cut.py
   ```

5. **成品檢驗**：
   - 成片位於 `out/cut/film_1080p.mp4`
   - 自審圖表位於 `out/review/film_1080p_pass1.jpg` 與 `film_1080p_pass5_cuts.jpg`
