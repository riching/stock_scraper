from flask import Flask, render_template, request, redirect, url_for
from app.models.stock import StockDatabase


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # API端点
    @app.route("/api/industries")
    def api_get_industries():
        """获取行业列表API"""
        try:
            db = StockDatabase()
            industries = db.get_industries()
            return {"success": True, "industries": industries}
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    @app.route("/api/industry/<industry_name>")
    def api_get_stocks_by_industry(industry_name):
        """获取指定行业的股票列表API"""
        try:
            page = int(request.args.get("page", 1))
            page_size = int(request.args.get("page_size", 100))
            page_size = min(page_size, 200)

            db = StockDatabase()
            result = db.get_stocks_by_industry(industry_name, page, page_size)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    @app.route("/api/stock/<stock_code>")
    def api_get_stock_detail(stock_code):
        """获取股票详情API"""
        try:
            db = StockDatabase()
            detail = db.get_stock_detail(stock_code)
            if not detail:
                return {"success": False, "error": "Stock not found"}, 404

            # 获取K线数据
            period = int(request.args.get("period", 120))
            kline_data = db.get_stock_kline_data(stock_code, period)

            detail["kline_data"] = kline_data
            return {"success": True, "data": detail}
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    @app.route("/api/search")
    def api_search_stocks():
        """搜索股票API"""
        try:
            query = request.args.get("q", "").strip()
            if not query:
                return {"success": False, "error": "Search query is required"}, 400

            page = int(request.args.get("page", 1))
            page_size = int(request.args.get("page_size", 50))
            page_size = min(page_size, 100)

            db = StockDatabase()
            result = db.search_stocks(query, page, page_size)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    # Web页面路由
    @app.route("/")
    def index():
        """首页 - 行业列表"""
        db = StockDatabase()
        industries = db.get_industries()
        return render_template("industries.html", industries=industries)

    @app.route("/industry/<industry_name>")
    def industry_stocks(industry_name):
        """行业股票列表"""
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 100))
        page_size = min(page_size, 200)

        db = StockDatabase()
        result = db.get_stocks_by_industry(industry_name, page, page_size)
        return render_template(
            "industry_stocks.html",
            industry_name=industry_name,
            stocks=result["stocks"],
            pagination=result["pagination"],
        )

    @app.route("/stock/<stock_code>")
    def stock_detail(stock_code):
        """股票详情"""
        db = StockDatabase()
        detail = db.get_stock_detail(stock_code)
        if not detail:
            return "Stock not found", 404

        kline_data = db.get_stock_kline_data(stock_code, 120)
        return render_template("stock_detail.html", stock=detail, kline_data=kline_data)

    @app.route("/search")
    def search():
        """搜索页面"""
        query = request.args.get("q", "").strip()
        if not query:
            return redirect(url_for("index"))

        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))
        page_size = min(page_size, 100)

        db = StockDatabase()
        result = db.search_stocks(query, page, page_size)
        if len(result["results"]) == 1:
            # 如果只有一个结果，直接跳转到详情页
            return redirect(
                url_for("stock_detail", stock_code=result["results"][0]["code"])
            )
        else:
            # 显示搜索结果列表
            return render_template(
                "search_results.html",
                query=query,
                results=result["results"],
                pagination=result["pagination"],
            )

    return app
