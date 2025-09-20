//+------------------------------------------------------------------+
//|                                                  TradingWebhookEA.mq5|
//|                        Fixed MQL5 Version (No Trade.mqh)            |
//+------------------------------------------------------------------+
#property strict

input string WebhookURL = "http://127.0.0.1:5000/webhook"; // Local Flask URL
input int PollingInterval = 5; // วินาที
input double DefaultVolume = 0.01; // Default lot size
input int Slippage = 10; // Slippage in points
input string TradeComment = "WebhookEA"; // Order comment
input int MagicNumber = 12345; // Magic number for orders

datetime last_poll_time = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("WebhookEA initialized. Polling URL: ", WebhookURL);
   Print("Make sure to add the URL to Tools->Options->Expert Advisors->Allow WebRequest");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   if (TimeCurrent() - last_poll_time < PollingInterval)
      return;
   
   string headers = "";
   char data[];
   char result[];
   string result_headers;
   int timeout = 5000;
   
   ResetLastError();
   
   int response = WebRequest(
      "GET",
      WebhookURL,
      headers,
      timeout,
      data,
      result,
      result_headers
   );
   
   if (response == 200 && ArraySize(result) > 0)
   {
      string json_result = CharArrayToString(result);
      Print("Webhook response: ", json_result);
      
      // Parse JSON response
      string action = GetValue(json_result, "action");
      string symbol = GetValue(json_result, "symbol");
      double volume = StringToDouble(GetValue(json_result, "volume"));
      
      // Use default volume if not specified
      if (volume <= 0)
         volume = DefaultVolume;
      
      // Validate symbol and action
      if (symbol == "" || action == "")
      {
         Print("Invalid signal: action=", action, ", symbol=", symbol);
         last_poll_time = TimeCurrent();
         return;
      }
      
      // Use current symbol if different symbol specified
      if (symbol != Symbol())
      {
         Print("Signal for different symbol: ", symbol, " (using current: ", Symbol(), ")");
         symbol = Symbol();
      }
      
      // Execute trades using native MQL5 functions
      if (action == "buy")
      {
         ExecuteBuyOrder(symbol, volume);
      }
      else if (action == "sell")
      {
         ExecuteSellOrder(symbol, volume);
      }
      else
      {
         Print("Unknown action: ", action);
      }
   }
   else
   {
      if (response != 200 && response != -1)
         Print("WebRequest failed with response code: ", response);
      
      int error = GetLastError();
      if (error != 0)
         Print("WebRequest error: ", error, " - ", GetErrorDescription(error));
   }
   
   last_poll_time = TimeCurrent();
}

//+------------------------------------------------------------------+
//| Execute Buy Order using MqlTradeRequest                         |
//+------------------------------------------------------------------+
void ExecuteBuyOrder(string symbol, double volume)
{
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_DEAL;
   request.symbol = symbol;
   request.volume = volume;
   request.type = ORDER_TYPE_BUY;
   request.price = SymbolInfoDouble(symbol, SYMBOL_ASK);
   request.deviation = Slippage;
   request.magic = MagicNumber;
   request.comment = TradeComment;
   request.type_filling = ORDER_FILLING_FOK;
   
   if (OrderSend(request, result))
   {
      Print("Buy order sent successfully for ", symbol, 
            " Volume: ", volume, 
            " Price: ", request.price,
            " Ticket: ", result.order);
   }
   else
   {
      Print("Failed to send buy order. Error: ", GetLastError(), 
            " Result: ", result.retcode, 
            " Comment: ", result.comment);
   }
}

//+------------------------------------------------------------------+
//| Execute Sell Order using MqlTradeRequest                        |
//+------------------------------------------------------------------+
void ExecuteSellOrder(string symbol, double volume)
{
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_DEAL;
   request.symbol = symbol;
   request.volume = volume;
   request.type = ORDER_TYPE_SELL;
   request.price = SymbolInfoDouble(symbol, SYMBOL_BID);
   request.deviation = Slippage;
   request.magic = MagicNumber;
   request.comment = TradeComment;
   request.type_filling = ORDER_FILLING_FOK;
   
   if (OrderSend(request, result))
   {
      Print("Sell order sent successfully for ", symbol, 
            " Volume: ", volume, 
            " Price: ", request.price,
            " Ticket: ", result.order);
   }
   else
   {
      Print("Failed to send sell order. Error: ", GetLastError(), 
            " Result: ", result.retcode, 
            " Comment: ", result.comment);
   }
}

//+------------------------------------------------------------------+
//| Simple JSON parser function                                      |
//+------------------------------------------------------------------+
string GetValue(string json, string key)
{
   string pattern = "\"" + key + "\":\"";
   int start = StringFind(json, pattern);
   
   if (start == -1) 
   {
      // Try without quotes (for numeric values)
      pattern = "\"" + key + "\":";
      start = StringFind(json, pattern);
      if (start == -1) return "";
      start += StringLen(pattern);
      
      // Skip whitespace
      while (start < StringLen(json) && StringGetCharacter(json, start) == 32)
         start++;
      
      // Find the end (comma, closing brace, or end of string)
      int end = start;
      while (end < StringLen(json))
      {
         int ch = StringGetCharacter(json, end);
         if (ch == 44 || ch == 125 || ch == 93) // comma, }, ]
            break;
         end++;
      }
      
      if (end <= start) return "";
      string value = StringSubstr(json, start, end - start);
      StringTrimLeft(value);
      StringTrimRight(value);
      return value;
   }
   
   start += StringLen(pattern);
   int end = StringFind(json, "\"", start);
   if (end == -1) return "";
   
   return StringSubstr(json, start, end - start);
}

//+------------------------------------------------------------------+
//| Get error description                                            |
//+------------------------------------------------------------------+
string GetErrorDescription(int error_code)
{
   switch(error_code)
   {
      case 4060: return "No internet connection";
      case 4014: return "Unknown symbol";
      case 4751: return "Invalid URL";
      case 4752: return "Failed to connect to specified URL";
      case 4753: return "Timeout exceeded";
      case 4754: return "HTTP error";
      case 5203: return "URL not allowed for WebRequest";
      case 4809: return "Resource not found";
      default: return "Error code: " + IntegerToString(error_code);
   }
}